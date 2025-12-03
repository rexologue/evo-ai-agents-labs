from aiogram import Router, F, Bot
import asyncio
from contextlib import asynccontextmanager
from src.services.request_manager import request_manager
from src.services.agent_connector import AgentConnector
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import src.keyboards as kb
from src.utils.session import session_store
from typing import Union, Optional, Dict, Tuple
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
from typing import TypedDict
from config import get_config
from src.services.request_manager import request_manager
from config.config import config
import telegramify_markdown
from telegramify_markdown.customize import get_runtime_config
from telegramify_markdown.type import ContentTypes
from src.utils.voice_processor import voice_processor

get_runtime_config().markdown_symbol.head_level_1 = "📌"  # If you want, Customizing the head level 1 symbol
get_runtime_config().markdown_symbol.head_level_2 = "✨"
get_runtime_config().markdown_symbol.head_level_3 = "➡️"
get_runtime_config().markdown_symbol.head_level_4 = "💡"
get_runtime_config().markdown_symbol.link = "🔗"  # If you want, Customizing the link symbol
from config import get_config
from src.services.request_manager import request_manager
from config.config import config
import telegramify_markdown
from telegramify_markdown.customize import get_runtime_config
from telegramify_markdown.type import ContentTypes
from src.utils.voice_processor import voice_processor

get_runtime_config().markdown_symbol.head_level_1 = "📌"  # If you want, Customizing the head level 1 symbol
get_runtime_config().markdown_symbol.head_level_2 = "✨"
get_runtime_config().markdown_symbol.head_level_3 = "➡️"
get_runtime_config().markdown_symbol.head_level_4 = "💡"
get_runtime_config().markdown_symbol.link = "🔗"  # If you want, Customizing the link symbol

router = Router(name=__name__)

class RequestData(TypedDict):
    original_text: str
    modified_text: str
    retry_count: int
    errors: list[str]

# User states and data storage
user_states: Dict[int, str] = {}
user_last_messages: Dict[int, Tuple[int, int]] = {}
user_request_data: Dict[int, RequestData] = {} 
user_failure_history: Dict[int, list] = {}

async def show_typing_indicator(chat_id: int, bot: Bot):
    """Show typing indicator"""
    try:
        await bot.send_chat_action(chat_id, "typing")
    except Exception as e:
        return

@asynccontextmanager
async def typing_context(chat_id: int, bot: Bot, interval: float = 4.0):
    """
    Context manager that shows typing indicator at regular intervals
    until the operation is complete
    """
    typing_task = None
    stop_typing = asyncio.Event()
    
    async def typing_worker():
        while not stop_typing.is_set():
            try:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                break
    
    try:
        typing_task = asyncio.create_task(typing_worker())
        yield
    finally:
        stop_typing.set()
        if typing_task:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task

async def cleanup_previous_messages(chat_id: int, bot: Bot) -> None:
    """Clean up previous system messages"""
    if chat_id in user_last_messages:
        last_bot_msg, last_user_msg = user_last_messages[chat_id]
        with suppress(TelegramBadRequest):
            await bot.delete_message(chat_id, last_bot_msg)
            await bot.delete_message(chat_id, last_user_msg)



async def send_clean_message(
    message: Union[Message, CallbackQuery], 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_cleanup: bool = False,
    reply_to_message_id: Optional[int] = None
) -> Optional[Message]:
    """Send new message with cleanup of previous ones"""
    # Проверяем наличие необходимых атрибутов
    if not message.from_user or not hasattr(message, 'bot') or message.bot is None:
        return None

    bot: Bot = message.bot  # Теперь точно знаем, что bot не None
    chat_id = message.from_user.id
    
    if not disable_cleanup:
        await cleanup_previous_messages(chat_id, bot)

        boxs = await telegramify_markdown.telegramify(
            content=text,
            interpreters_use=None,
            latex_escape=True,
            normalize_whitespace=True,
            max_word_count=4090  # The maximum number of words in a single message.
        )

        for item in boxs:
            if item.content_type == ContentTypes.TEXT:
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=item.content,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2",
                    reply_to_message_id=reply_to_message_id
                )
                
                # Get message ID based on type
                if isinstance(message, CallbackQuery) and message.message:
                    user_msg_id = message.message.message_id
                elif isinstance(message, Message):
                    user_msg_id = message.message_id
                else:
                    return None
                
                                # Get message ID based on type
                if isinstance(message, CallbackQuery) and message.message:
                        user_msg_id = message.message.message_id
                elif isinstance(message, Message):
                        user_msg_id = message.message_id
                else:
                        return None
                    
                    # Save new message IDs
                user_last_messages[chat_id] = (sent_msg.message_id, user_msg_id)
                return sent_msg

        boxs = await telegramify_markdown.telegramify(
            content=text,
            interpreters_use=None,
            latex_escape=True,
            normalize_whitespace=True,
            max_word_count=4090  # The maximum number of words in a single message.
        )

        for item in boxs:
            if item.content_type == ContentTypes.TEXT:
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=item.content,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2",
                    reply_to_message_id=reply_to_message_id
                )
                
                # Get message ID based on type
                if isinstance(message, CallbackQuery) and message.message:
                    user_msg_id = message.message.message_id
                elif isinstance(message, Message):
                    user_msg_id = message.message_id
                else:
                    return None
                
                                # Get message ID based on type
                if isinstance(message, CallbackQuery) and message.message:
                        user_msg_id = message.message.message_id
                elif isinstance(message, Message):
                        user_msg_id = message.message_id
                else:
                        return None
                    
                    # Save new message IDs
                user_last_messages[chat_id] = (sent_msg.message_id, user_msg_id)
                return sent_msg

def create_retry_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with retry button"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔄 Retry", callback_data="retry_request"))
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_retry"))
    return builder.as_markup()

async def log_failure(user_id: int, error: str, request_data: str):
    """Log failure details for the user"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user_id not in user_failure_history:
        user_failure_history[user_id] = []
    
    user_failure_history[user_id].append({
        "timestamp": timestamp,
        "error": error,
        "request_data": request_data
    })

async def show_failure_history(user_id: int, bot: Bot, chat_id: int):
    """Show failure history to user"""
    if user_id in user_failure_history and user_failure_history[user_id]:
        history_text = "⏳ Failure History:\n"
        for idx, entry in enumerate(user_failure_history[user_id], 1):
            history_text += (
                f"\n#{idx} - {entry['timestamp']}\n"
                f"Error: {entry['error']}\n"
                f"Data: {entry['request_data'][:50]}...\n"
            )
        
        await bot.send_message(
            chat_id=chat_id,
            text=history_text
        )
        user_failure_history[user_id] = []

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_states[user_id] = "main_menu"
    await send_clean_message(
        message,
        "Добро пожаловать в AI-AGENTS!",
        kb.main_menu
    )

@router.callback_query(F.data == "retry_request")
async def retry_request(callback: CallbackQuery):
    """Handle retry of failed request"""
    if not callback.from_user or not callback.message:
        return await callback.answer("Invalid request")

    user_id = callback.from_user.id
    
    if user_id not in user_request_data:
        return await callback.answer("No request to retry")
    
    request_data = user_request_data[user_id]
    original_text = request_data['original_text']
    modified_text = request_data['modified_text']
    retry_count = request_data.get('retry_count', 0) + 1
    
    # Update request data
    user_request_data[user_id] = {
        'original_text': original_text,
        'modified_text': modified_text,
        'retry_count': retry_count,
        'errors': request_data.get('errors', [])
    }
    bot: Bot = callback.bot
    # Delete previous messages
    await cleanup_previous_messages(user_id, bot)
    
    # Send processing message
    processing_msg = await callback.message.answer(
        f"🔄 Retrying request (attempt #{retry_count})...",
        reply_markup=create_retry_keyboard(),
        reply_to_message_id=callback.message.message_id
    )
    
    # Store message IDs
    user_last_messages[user_id] = (processing_msg.message_id, callback.message.message_id)
    
    # Process the request
    try:
        if agent := session_store.get_agent(user_id):
            # Use typing context manager
            async with typing_context(user_id, bot):
                response = await agent.send_message(modified_text)
                
                # On success - show response and failure history
                await callback.message.answer(
                    f"Agent response: {response}",
                    reply_to_message_id=callback.message.message_id
                )
                await show_failure_history(user_id, bot, user_id)
                
                # Cleanup
                del user_request_data[user_id]
                await cleanup_previous_messages(user_id, bot)
    except Exception as e:
        error_msg = str(e)
        await log_failure(user_id, error_msg, modified_text)
        
        # Update request data with error
        if user_id in user_request_data:
            user_request_data[user_id]['errors'].append(error_msg)
        
        # Show error with retry option
        await send_clean_message(
            callback,
            f"❌ Attempt #{retry_count} failed:\n{error_msg}",
            reply_markup=create_retry_keyboard(),
            disable_cleanup=True,
            reply_to_message_id=callback.message.message_id
        )

@router.callback_query(F.data == "cancel_retry")
async def cancel_retry(callback: CallbackQuery):
    """Cancel retry attempts"""
    if not callback.from_user:
        return

    user_id = callback.from_user.id
    
    if user_id in user_request_data:
        del user_request_data[user_id]
    
    await send_clean_message(
        callback,
        "❌ Retry attempts canceled",
        reply_markup=kb.main_menu
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = "main_menu"
    await send_clean_message(
        callback,
        "Главное меню:",
        kb.main_menu
    )

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = "help_menu"
    await send_clean_message(
        callback,
        "Раздел помощи:\nЗдесь будет справочная информация",
        kb.help_menu
    )

@router.callback_query(F.data == "start_work")
async def start_work(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = "start_work_menu"
    await send_clean_message(
        callback,
        "Начало работы с агентом:",
        kb.start_work_menu
    )

@router.callback_query(F.data == "connect_to_chat")
async def request_agent_url(callback: CallbackQuery):
    user_id = callback.from_user.id
    config = get_config()
    
    try:
        agent_uri = config.PUBLIC_URL
        
        if not agent_uri:
            raise ValueError("PUBLIC_URL not configured")
            
        session_store.connect_agent(user_id, agent_uri)
        user_states[user_id] = "connected"
        
        await send_clean_message(
            callback,
            f"✅ Successfully connected to agent!\n• URI: {agent_uri}\n• Status: Healthy\n\nYou can now chat with the agent.",
            kb.disconnect_menu
        )
    except Exception as e:
        await send_clean_message(
            callback,
            f"❌ Connection failed: {str(e)}",
            kb.connect_cancel_menu
        )
    config = get_config()
    
    try:
        agent_uri = config.PUBLIC_URL
        
        if not agent_uri:
            raise ValueError("PUBLIC_URL not configured")
            
        session_store.connect_agent(user_id, agent_uri)
        user_states[user_id] = "connected"
        
        await send_clean_message(
            callback,
            f"✅ Successfully connected to agent!\n• URI: {agent_uri}\n• Status: Healthy\n\nYou can now chat with the agent.",
            kb.disconnect_menu
        )
    except Exception as e:
        await send_clean_message(
            callback,
            f"❌ Connection failed: {str(e)}",
            kb.connect_cancel_menu
        )

@router.callback_query(F.data == "cancel_connect")
async def cancel_connect(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = "start_work_menu"
    await send_clean_message(
        callback,
        "Подключение отменено:",
        kb.start_work_menu
    )

@router.callback_query(F.data == "disconnect")
async def disconnect_agent(callback: CallbackQuery):
    user_id = callback.from_user.id
    session_store.disconnect_agent(user_id)
    user_states[user_id] = "main_menu"
    await send_clean_message(
        callback,
        "✅ Вы отключены от агента",
        kb.main_menu
    )

@router.message(F.voice | F.audio | F.video_note)
async def handle_voice_message(message: Message):
    """Handle voice messages, audio files, and video notes"""
    if not message.from_user or not message.bot:
        return

    user_id = message.from_user.id
    bot = message.bot
    
    if user_states.get(user_id) != "connected":
        await message.answer(
            "❌ Please connect to an agent first using /start_work",
            reply_to_message_id=message.message_id
        )
        return
    
    # Send processing message
    processing_msg = await message.answer(
        "🎤 Processing voice message...",
        reply_to_message_id=message.message_id
    )
    
    try:
        # Process voice message using VoiceProcessor
        transcribed_text, error_message = await voice_processor.process_voice_message(bot, message)
        
        if error_message:
            await processing_msg.edit_text(f"❌ {error_message}")
            return
        
        # Show transcription to user
        if len(transcribed_text) > 1000:
            # Truncate very long transcriptions
            display_text = transcribed_text[:1000] + "..."
        else:
            display_text = transcribed_text
            
        await processing_msg.edit_text(
            f"📝 Transcribed ({len(transcribed_text)} chars):\n{display_text}\n\nSending to agent..."
        )
        
        # Store request data
        user_request_data[user_id] = {
            'original_text': f"[Voice message: {len(transcribed_text)} chars]",
            'modified_text': transcribed_text,
            'retry_count': 0,
            'errors': []
        }
        
        # Send to agent with typing indicator
        if agent := session_store.get_agent(user_id):
            # Use typing context manager
            async with typing_context(user_id, bot):
                response = await agent.send_message(transcribed_text)
                
                # Send agent response
                await send_clean_message(
                    message,
                    response,
                    reply_to_message_id=message.message_id
                )
                
                # Cleanup
                if user_id in user_request_data:
                    del user_request_data[user_id]
                
    except Exception as e:
        error_msg = str(e)        
        await processing_msg.edit_text(
            f"❌ Error processing voice message:\n{error_msg}",
            reply_markup=create_retry_keyboard()
        )
        
        # Store error for potential retry
        if user_id in user_request_data:
            user_request_data[user_id]['errors'].append(error_msg)

@router.message()
async def handle_agent_chat(message: Message):
    if not message.from_user or not message.text or not message.bot:
        return
    
    if voice_processor.is_supported_message(message):
        return
    
    if voice_processor.is_supported_message(message):
        return

    user_id = message.from_user.id
    bot = message.bot
    
    if user_states.get(user_id) == "connected":
        if agent := session_store.get_agent(user_id):
            modified_text = message.text
            
            async def process_request():
                try:
                    # Use typing context manager
                    async with typing_context(user_id, bot):
                        max_retries = 3
                        response = await agent.send_message(modified_text, max_retries=max_retries)
                        
                        current_task = asyncio.current_task()
                        if current_task and current_task.cancelled():
                            return
                        
                        if "🚨 Task failed after" in response:
                            await log_failure(user_id, response, modified_text)
                            
                            if user_id in user_request_data:
                                user_request_data[user_id]['errors'].append(response)
                            
                            sent_msg = await bot.send_message(
                                chat_id=user_id,
                                text=f"❌ Все попытки завершились ошибкой:\n{response}",
                                reply_markup=create_retry_keyboard(),
                                reply_to_message_id=message.message_id
                            )
                            
                            if sent_msg:
                                user_last_messages[user_id] = (sent_msg.message_id, message.message_id)
                        else:
                            # Отправляем очищенный текст ответа
                            await send_clean_message(message, response, reply_to_message_id=message.message_id)
                            
                            if user_id in user_request_data:
                                del user_request_data[user_id]
                                
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    current_task = asyncio.current_task()
                    if current_task and current_task.cancelled():
                        return
                        
                    error_msg = str(e)
                    await log_failure(user_id, error_msg, modified_text)
                    
                    if user_id in user_request_data:
                        user_request_data[user_id]['errors'].append(error_msg)
                    
                    sent_msg = await bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Ошибка:\n{error_msg}",
                        reply_markup=create_retry_keyboard(),
                        reply_to_message_id=message.message_id
                    )
                    
                    if sent_msg:
                        user_last_messages[user_id] = (sent_msg.message_id, message.message_id)
            
            task = asyncio.create_task(process_request())
            request_manager.add_request(user_id, task)

@router.edited_message()
async def handle_edited_message(message: Message):
    """Handle edited messages based on configuration"""
    if not message.from_user or not message.text or not config.HANDLE_MESSAGE_EDITS:
        return
    
    user_id = message.from_user.id
    
    if user_states.get(user_id) == "connected":
        # Отменяем предыдущий запрос если он активен
        request_manager.cancel_request(user_id)
        
        # Обрабатываем новый запрос
        await handle_agent_chat(message)