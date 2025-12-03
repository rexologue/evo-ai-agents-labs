import json
import logging
import uuid
import httpx
import asyncio
from contextlib import suppress
from typing import Optional, Dict, Any, List
from opentelemetry import trace
from a2a.types import Part, TextPart, DataPart
from a2a.agent_execution import RequestContext
from a2a.utils.errors import ServerError

logger = logging.getLogger(__name__)

class AgentConnector:
    def __init__(self, agent_url: str):
        if not agent_url.endswith('/'):
            agent_url += '/'
            
        self.agent_url = agent_url
        self.session = httpx.AsyncClient(
            base_url=agent_url,
            timeout=httpx.Timeout(180.0, connect=30.0),
        )
        self.tracer = trace.get_tracer(__name__)
        self.request_id = 0

    async def send_message(self, text_msg: str, max_retries: int = 3) -> str:
        """Send message to agent with retry logic for a2a errors"""
        with self.tracer.start_as_current_span(
            "agent_connector_send_message",
            attributes={
                "agent.url": self.agent_url,
                "input.message": text_msg,
                "input.length": len(text_msg),
                "max_retries": max_retries
            }
        ) as span:
            for attempt in range(max_retries):
                try:
                    result = await self._send_single_message(text_msg, span, attempt + 1)
                    
                    # Check if response contains a2a task failure
                    if self._is_a2a_task_failure(result):
                        if attempt < max_retries - 1:
                            retry_delay = 2.0 * (2 ** attempt)  # Exponential backoff
                            logger.warning(
                                f"a2a task failed, retrying in {retry_delay}s "
                                f"(attempt {attempt + 1}/{max_retries}): {result}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            # Final attempt failed
                            return result
                    
                    # Success or non-retryable error
                    return result
                    
                except Exception as e:
                    error_id = str(uuid.uuid4())
                    if attempt < max_retries - 1:
                        retry_delay = 1.0 * (2 ** attempt)
                        logger.warning(
                            f"Request failed, retrying in {retry_delay}s "
                            f"(attempt {attempt + 1}/{max_retries}): {str(e)}"
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Final attempt failed (ID: {error_id}): {str(e)}", exc_info=True)
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        return f"🚨 Task failed after {max_retries} attempts (ID: {error_id})\n• Error: {str(e)}"

    def _is_a2a_task_failure(self, response_text: str) -> bool:
        """Check if response indicates a2a task failure that should be retried"""
        try:
            # Try to parse as JSON first
            if response_text.strip().startswith('{'):
                response_data = json.loads(response_text)
                
                # Check for a2a task failure structure
                if isinstance(response_data, dict):
                    # Check for the specific error structure you provided
                    if (response_data.get('kind') == 'task' and 
                        response_data.get('status', {}).get('state') == 'failed'):
                        return True
                    
                    # Check for other retryable a2a error patterns
                    if ('error' in response_data and 
                        response_data.get('error', {}).get('code') in [-32000, -32603]):  # Common retryable errors
                        return True
            
            # Check for string patterns indicating retryable errors
            retryable_patterns = [
                'Task failed',
                'failed',
                'timeout',
                'connection',
                'network',
                'server error',
                'gateway'
            ]
            
            response_lower = response_text.lower()
            return any(pattern in response_lower for pattern in retryable_patterns)
            
        except json.JSONDecodeError:
            # If not JSON, check string patterns
            response_lower = response_text.lower()
            retryable_patterns = ['task failed', 'failed', 'timeout', 'connection']
            return any(pattern in response_lower for pattern in retryable_patterns)

    async def _send_single_message(self, text_msg: str, span: trace.Span, attempt: int) -> str:
        """Send a single message attempt"""
        span.set_attribute(f"attempt.{attempt}.input", text_msg)
        
        try:
            payload = self._create_payload(text_msg)
            
            response = await self.session.post(
                "",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            span.set_attribute(f"attempt.{attempt}.status_code", response.status_code)
            
            if response.status_code == 200:
                result = self._process_response(response, text_msg, span)
                span.set_attribute(f"attempt.{attempt}.success", True)
                return result
            else:
                error_result = self._handle_http_error(response, text_msg, span)
                span.set_attribute(f"attempt.{attempt}.success", False)
                span.set_attribute(f"attempt.{attempt}.error", error_result)
                return error_result
                
        except Exception as e:
            span.set_attribute(f"attempt.{attempt}.success", False)
            span.set_attribute(f"attempt.{attempt}.error", str(e))
            raise e

    def _create_payload(self, text_msg: str) -> Dict[str, Any]:
        """Create RPC payload for agent request using a2a standards"""
        self.request_id += 1
        message_id = str(uuid.uuid4())
        
        # Use a2a's TextPart for proper message construction
        text_part = TextPart(text=text_msg)
        
        return {
            "jsonrpc": "2.0",
            "id": str(self.request_id),
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": message_id,
                    "parts": [text_part.model_dump()],  # Use model_dump() for Pydantic v2
                    "role": "user"
                },
                "configuration": {
                    "acceptedOutputModes": ["text/plain", "application/json"],
                    "historyLength": 10,  # Increased context window
                    "blocking": True,
                    "timeout": 120000  # 2 minutes timeout in ms
                }
            }
        }

    def _process_response(self, response: httpx.Response, original_msg: str, span: trace.Span) -> str:
        """Process agent response according to a2a standards and extract text"""
        try:
            response_data = response.json()
            
            # Check for JSON-RPC error response
            if "error" in response_data:
                error = response_data["error"]
                error_msg = f"{error.get('message', 'Unknown error')} (code: {error.get('code', 'unknown')})"
                span.set_attribute("error.message", error_msg)
                return f"🚨 API Error\n• Error: {error_msg}"
            
            # Process successful response
            result = response_data.get("result", {})
            
            # Extract text from different a2a response formats
            response_text = self._extract_text_from_a2a_response(result)
            
            if response_text:
                span.set_attribute("output.message", response_text)
                span.set_attribute("output.length", len(response_text))
                return response_text
            
            # Fallback: return string representation of result
            result_str = str(result)
            span.set_attribute("output.message", result_str)
            return result_str
                
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {response.text[:200]}..."
            span.set_attribute("error.message", error_msg)
            return f"🚨 Invalid Response\n• Error: {error_msg}"

    def _extract_text_from_a2a_response(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract text content from various a2a response formats"""
        text_parts = []
        
        # Format 1: Response with artifacts
        if "artifacts" in result:
            artifacts = result["artifacts"]
            if isinstance(artifacts, dict):
                artifacts = [artifacts]  # Convert single artifact to list
            
            for artifact in artifacts if isinstance(artifacts, list) else []:
                if "parts" in artifact:
                    artifact_text = self._extract_text_from_parts(artifact["parts"])
                    if artifact_text:
                        text_parts.append(artifact_text)
        
        # Format 2: Response with message containing parts
        elif "message" in result and "parts" in result["message"]:
            message_text = self._extract_text_from_parts(result["message"]["parts"])
            if message_text:
                text_parts.append(message_text)
        
        # Format 3: Direct text response
        elif "text" in result:
            text_parts.append(result["text"])
        
        # Format 4: Nested response field
        elif "response" in result and isinstance(result["response"], dict):
            if "text" in result["response"]:
                text_parts.append(result["response"]["text"])
            elif "result" in result["response"]:
                text_parts.append(str(result["response"]["result"]))
        
        # Format 5: Check for markdown/code blocks in any text field
        if not text_parts:
            # Recursively search for text fields in the entire result
            text_parts.extend(self._find_text_fields(result))
        
        # Clean and format the final text
        if text_parts:
            final_text = "\n\n".join(text_parts)
            return self._clean_response_text(final_text)
        
        return None

    def _find_text_fields(self, data: Any, max_depth: int = 3) -> List[str]:
        """Recursively find all text fields in the response"""
        text_fields = []
        
        if max_depth <= 0:
            return text_fields
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.strip():
                    # Prioritize fields that likely contain response text
                    if key in ['text', 'result', 'content', 'response', 'output', 'answer']:
                        text_fields.insert(0, value)  # Put important fields first
                    else:
                        text_fields.append(value)
                elif isinstance(value, (dict, list)):
                    text_fields.extend(self._find_text_fields(value, max_depth - 1))
        
        elif isinstance(data, list):
            for item in data:
                text_fields.extend(self._find_text_fields(item, max_depth - 1))
        
        return text_fields

    def _clean_response_text(self, text: str) -> str:
        """Clean and format the response text for Telegram"""
        # Remove excessive markdown code blocks but keep the content
        lines = text.split('\n')
        cleaned_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                # Skip the code block markers but keep the content
                continue
            cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Trim excessive whitespace
        cleaned_text = '\n'.join(line.strip() for line in cleaned_text.split('\n') if line.strip())
        
        # Limit length for Telegram (max 4096 characters)
        if len(cleaned_text) > 4000:
            cleaned_text = cleaned_text[:4000] + "...\n\n[Сообщение было сокращено из-за ограничения длины]"
        
        return cleaned_text

    def _extract_text_from_parts(self, parts: List[Dict]) -> str:
        """Extract text content from a2a message parts"""
        text_parts = []
        
        for part_data in parts:
            try:
                if isinstance(part_data, dict):
                    if part_data.get("kind") == "text":
                        text_parts.append(part_data.get("text", ""))
                    elif part_data.get("kind") == "data":
                        # Format data as JSON string or extract text
                        data_content = part_data.get("data", {})
                        if isinstance(data_content, dict) and "text" in data_content:
                            text_parts.append(data_content["text"])
                        else:
                            text_parts.append(json.dumps(data_content, ensure_ascii=False, indent=2))
            except (KeyError, TypeError) as e:
                logger.warning(f"Failed to parse part: {part_data}, error: {e}")
                continue
        
        return "\n\n".join(text_parts) if text_parts else ""

    def _handle_http_error(self, response: httpx.Response, original_msg: str, span: trace.Span) -> str:
        """Handle HTTP errors with specific messaging"""
        error_id = str(uuid.uuid4())
        
        if response.status_code == 404:
            error_msg = "Agent endpoint not found. Please check the agent URL."
        elif response.status_code == 401:
            error_msg = "Authentication failed. Please check your credentials."
        elif response.status_code == 403:
            error_msg = "Access forbidden. You don't have permission to access this agent."
        elif 500 <= response.status_code < 600:
            error_msg = f"Agent server error (HTTP {response.status_code}). Please try again later."
        else:
            error_msg = f"Unexpected HTTP error: {response.status_code}"
        
        span.set_attribute("error.message", error_msg)
        span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
        
        return f"🚨 Connection Error (ID: {error_id})\n• Error: {error_msg}"

    async def health_check(self) -> bool:
        """Check if the agent is reachable and healthy"""
        try:
            # Попробуйте разные эндпоинты для health check
            endpoints_to_try = ["/health", "/", "/status"]
            
            for endpoint in endpoints_to_try:
                try:
                    response = await self.session.get(endpoint, timeout=10.0)
                    if response.status_code == 200:
                        return True
                except (httpx.RequestError, httpx.TimeoutException):
                    continue
            
            # Если ни один эндпоинт не ответил, пробуем основной метод
            try:
                response = await self.session.head("", timeout=5.0)
                return response.status_code < 500
            except (httpx.RequestError, httpx.TimeoutException):
                return False
                
        except Exception:
            return False

    async def close(self):
        """Clean up resources"""
        await self.session.aclose()