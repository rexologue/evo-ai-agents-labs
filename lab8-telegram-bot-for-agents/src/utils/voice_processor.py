import os
import tempfile
import io
import asyncio
from typing import Optional, Tuple
import logging
from contextlib import suppress

import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """Class to handle voice message processing and transcription"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.supported_formats = ['.ogg', '.mp3', '.wav', '.m4a', '.mp4']
        
    async def process_voice_message(self, bot: Bot, message: Message) -> Tuple[Optional[str], Optional[str]]:
        """
        Process voice message and return (transcribed_text, error_message)
        """
        try:
            # Get file ID based on message type
            file_id, mime_type = self._get_file_info(message)
            if not file_id:
                return None, "Unsupported message type"
            
            # Download voice message
            voice_data = await self.download_voice_message(bot, file_id)
            if not voice_data:
                return None, "Failed to download voice message"
            
            # Convert to text
            transcribed_text = await self.convert_voice_to_text(voice_data, mime_type)
            if not transcribed_text:
                return None, "Could not transcribe voice message"
            
            return transcribed_text, None
            
        except Exception as e:
            logger.error(f"Voice message processing failed: {e}")
            return None, f"Error processing voice message: {str(e)}"
    
    def _get_file_info(self, message: Message) -> Tuple[Optional[str], Optional[str]]:
        """Get file ID and MIME type from message"""
        if message.voice:
            return message.voice.file_id, "audio/ogg"
        elif message.audio:
            return message.audio.file_id, message.audio.mime_type or "audio/mpeg"
        elif message.video_note:
            return message.video_note.file_id, "video/mp4"
        return None, None
    
    async def download_voice_message(self, bot: Bot, file_id: str) -> Optional[bytes]:
        """Download voice message file"""
        try:
            file = await bot.get_file(file_id)
            file_data = await bot.download_file(file.file_path)
            return file_data.getvalue() if hasattr(file_data, 'getvalue') else file_data
        except Exception as e:
            logger.error(f"Failed to download voice message: {e}")
            return None
    
    async def convert_voice_to_text(self, voice_data: bytes, mime_type: str, language: str = "ru-RU") -> Optional[str]:
        """Convert voice message to text using various methods"""
        try:
            # Convert to WAV format first
            wav_data = await self._convert_to_wav(voice_data, mime_type)
            if not wav_data:
                return None
            
            # Try different recognition methods in order of preference
            methods = [
                self._try_whisper,
                self._try_google_speech,
                self._try_speech_recognition_engines
            ]
            
            for method in methods:
                try:
                    text = await method(wav_data, language)
                    if text and text.strip():
                        logger.info(f"Successfully transcribed using {method.__name__}")
                        return text.strip()
                except Exception as e:
                    logger.warning(f"{method.__name__} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Voice to text conversion failed: {e}")
            return None
    
    async def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> Optional[bytes]:
        """Convert audio data to WAV format"""
        try:
            # Check if ffmpeg is available
            try:
                from pydub.utils import which
                if not which("ffmpeg"):
                    logger.warning("FFmpeg not found. Audio conversion may not work properly.")
            except ImportError:
                pass
            
            # Determine format from MIME type or file signature
            format_name = self._get_format_from_mime(mime_type)
            
            # Convert using pydub
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format_name)
            
            # Export to WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            return wav_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            # Fallback: try to use the original data if it's already WAV-like
            if mime_type in ["audio/wav", "audio/x-wav"]:
                return audio_data
            return None
    
    def _get_format_from_mime(self, mime_type: str) -> str:
        """Get format name from MIME type"""
        mime_to_format = {
            "audio/ogg": "ogg",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/m4a": "m4a",
            "video/mp4": "mp4",
        }
        return mime_to_format.get(mime_type, "ogg")  # default to ogg
    
    async def _try_whisper(self, wav_data: bytes, language: str) -> Optional[str]:
        """Try using OpenAI Whisper for speech recognition"""
        try:
            import whisper
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file.flush()
                
                # Load model and transcribe
                model = whisper.load_model("base")
                result = model.transcribe(
                    temp_file.name, 
                    language=language.split('-')[0],
                    fp16=False  # Disable FP16 for better compatibility
                )
                
                os.unlink(temp_file.name)
                return result['text']
                
        except ImportError:
            logger.warning("Whisper not installed")
            raise
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise
    
    async def _try_google_speech(self, wav_data: bytes, language: str) -> Optional[str]:
        """Try using Google Speech Recognition"""
        try:
            with sr.AudioFile(io.BytesIO(wav_data)) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=language)
                return text
                
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            raise
        except sr.RequestError as e:
            logger.error(f"Google Speech Recognition service error: {e}")
            raise
    
    async def _try_speech_recognition_engines(self, wav_data: bytes, language: str) -> Optional[str]:
        """Try different speech recognition engines"""
        engines = [
            ('sphinx', lambda audio: self.recognizer.recognize_sphinx(audio, language=language)),
            ('google_cloud', lambda audio: self.recognizer.recognize_google_cloud(audio, language=language)),
            ('bing', lambda audio: self.recognizer.recognize_bing(audio, language=language)),
        ]
        
        with sr.AudioFile(io.BytesIO(wav_data)) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = self.recognizer.record(source)
            
            for engine_name, recognize_func in engines:
                try:
                    text = recognize_func(audio_data)
                    logger.info(f"Successfully transcribed using {engine_name}")
                    return text
                except Exception as e:
                    logger.warning(f"{engine_name} recognition failed: {e}")
                    continue
        
        raise Exception("All speech recognition engines failed")
    
    def get_supported_types(self) -> list:
        """Get list of supported message types"""
        return ["voice", "audio", "video_note"]
    
    def is_supported_message(self, message: Message) -> bool:
        """Check if message contains supported voice/audio content"""
        return any([
            message.voice is not None,
            message.audio is not None,
            message.video_note is not None
        ])

# Global instance
voice_processor = VoiceProcessor()