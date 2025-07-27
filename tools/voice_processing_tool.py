"""
FIXED Voice Processing Tool for Kisan Mitra using ElevenLabs API
Handles Speech-to-Text (Google Cloud) and Text-to-Speech (ElevenLabs)
Supports multiple Indian regional languages
Works with both WhatsApp (Twilio) and ADK Web platforms
Enhanced with better error handling and logging
"""

import os
import logging
import tempfile
import requests
import json
from typing import Tuple, Optional, Dict, Any
from google.cloud import speech  # For STT (Speech-to-Text)
import base64

logger = logging.getLogger(__name__)

class EnhancedVoiceProcessor:
    """Enhanced voice processor with better error handling and logging"""
    
    def __init__(self):
        """Initialize ElevenLabs and Google Cloud clients"""
        # ElevenLabs configuration
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "sk_371629025b120c623098bf5c61eaa8d2bf0242e8f1177187")
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        
        # Google Cloud Speech-to-Text (for voice recognition)
        try:
            self.speech_client = speech.SpeechClient()
            print("✅ Google Cloud Speech client initialized")
            logger.info("✅ Google Cloud Speech client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Google Cloud Speech client: {e}")
            logger.error(f"❌ Failed to initialize Google Cloud Speech client: {e}")
            self.speech_client = None
        
        if not self.elevenlabs_api_key:
            print("⚠️ ElevenLabs API key not found. Voice generation will be disabled.")
            logger.warning("⚠️ ElevenLabs API key not found. Voice generation will be disabled.")
        else:
            print("✅ ElevenLabs API key configured")
            logger.info("✅ ElevenLabs API key configured")
    
    # Language mapping for Indian regional languages
    LANGUAGE_CODES = {
        "hindi": "hi-IN",
        "english": "en-IN", 
        "punjabi": "pa-IN",
        "bengali": "bn-IN",
        "tamil": "ta-IN",
        "telugu": "te-IN",
        "marathi": "mr-IN",
        "gujarati": "gu-IN",
        "kannada": "kn-IN",
        "malayalam": "ml-IN",
        "odia": "or-IN",
        "assamese": "as-IN",
        "urdu": "ur-IN"
    }
    
    # ElevenLabs voice IDs for Indian languages (using multilingual voices)
    ELEVENLABS_VOICES = {
        "hi-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (multilingual, good for Hindi)
        "en-IN": "EXAVITQu4vr4xnSDxMaL",  # Bella (good for Indian English)
        "pa-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Punjabi)
        "bn-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Bengali)
        "ta-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Tamil)
        "te-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Telugu)
        "mr-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Marathi)
        "gu-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Gujarati)
        "kn-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Kannada)
        "ml-IN": "pNInz6obpgDQGcFmaJgB",  # Adam (works for Malayalam)
    }
    
    def detect_language_from_context(self, farmer_language: str = "hindi") -> str:
        """Detect language code from farmer context"""
        farmer_lang = farmer_language.lower()
        return self.LANGUAGE_CODES.get(farmer_lang, "hi-IN")  # Default to Hindi
    
    def enhanced_speech_to_text_from_url(self, media_url: str, auth_tuple: Tuple[str, str], language_code: str = "hi-IN") -> Optional[str]:
        """
        ENHANCED speech-to-text with multiple format attempts and better error handling
        """
        if not self.speech_client:
            print("❌ Speech client not initialized")
            logger.error("❌ Speech client not initialized")
            return None
            
        try:
            print(f"\n🎤 PROCESSING VOICE MESSAGE:")
            print(f"   📱 URL: {media_url}")
            print(f"   🌍 Language: {language_code}")
            
            # Download audio with better headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; KisanMitra/1.0)',
                'Accept': 'audio/*,*/*'
            }
            
            response = requests.get(media_url, auth=auth_tuple, timeout=30, headers=headers)
            print(f"   📥 Download Status: {response.status_code}")
            print(f"   📊 Audio Size: {len(response.content)} bytes")
            print(f"   📋 Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code != 200:
                print(f"   ❌ Download failed: {response.status_code}")
                logger.error(f"❌ Failed to download audio: {response.status_code}")
                return None
                
            audio_data = response.content
            
            if len(audio_data) == 0:
                print("   ❌ Audio data is empty")
                logger.error("❌ Audio data is empty")
                return None
            
            # Multiple audio configuration attempts
            audio_configs = [
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                    "sample_rate_hertz": 16000,
                    "name": "OGG_OPUS_16kHz"
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                    "sample_rate_hertz": 8000,
                    "name": "OGG_OPUS_8kHz"
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                    "sample_rate_hertz": 16000,
                    "name": "WEBM_OPUS_16kHz"
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                    "sample_rate_hertz": 48000,
                    "name": "WEBM_OPUS_48kHz"
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
                    "sample_rate_hertz": 16000,
                    "name": "MP3_16kHz"
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    "sample_rate_hertz": 16000,
                    "name": "LINEAR16_16kHz"
                }
            ]
            
            print(f"   🧪 Trying {len(audio_configs)} different audio configurations...")
            
            for i, config_data in enumerate(audio_configs, 1):
                try:
                    print(f"   🔄 Attempt {i}/{len(audio_configs)}: {config_data['name']}")
                    
                    config = speech.RecognitionConfig(
                        encoding=config_data["encoding"],
                        sample_rate_hertz=config_data["sample_rate_hertz"],
                        language_code=language_code,
                        enable_automatic_punctuation=True,
                        model="latest_short",  # Changed from latest_long for better voice message handling
                        use_enhanced=True,
                        # Add alternative language codes for better recognition
                        alternative_language_codes=["en-IN", "hi-IN"] if language_code not in ["en-IN", "hi-IN"] else []
                    )
                    
                    audio = speech.RecognitionAudio(content=audio_data)
                    
                    # Perform speech recognition
                    recognition_response = self.speech_client.recognize(config=config, audio=audio)
                    
                    if recognition_response.results:
                        transcript = recognition_response.results[0].alternatives[0].transcript
                        confidence = recognition_response.results[0].alternatives[0].confidence
                        
                        print(f"   ✅ SUCCESS with {config_data['name']}!")
                        print(f"   📝 Transcript: {transcript}")
                        print(f"   🎯 Confidence: {confidence:.2f}")
                        
                        if confidence > 0.3:  # Accept if confidence is reasonable
                            logger.info(f"✅ Speech recognized with {config_data['name']} (confidence: {confidence:.2f}): {transcript[:50]}...")
                            return transcript
                        else:
                            print(f"   ⚠️ Low confidence ({confidence:.2f}), trying next config...")
                    else:
                        print(f"   ❌ No results with {config_data['name']}")
                        
                except Exception as config_error:
                    print(f"   ❌ Config {config_data['name']} failed: {config_error}")
                    logger.warning(f"Config {config_data['name']} failed: {config_error}")
                    continue
            
            print("   ❌ All audio configurations failed")
            logger.error("❌ All audio configurations failed")
            return None
                
        except Exception as e:
            print(f"   ❌ Speech recognition error: {e}")
            logger.error(f"❌ Error in enhanced speech recognition from URL: {e}")
            return None
    
    def text_to_speech_elevenlabs(self, text: str, language_code: str = "hi-IN") -> Optional[str]:
        """
        Convert text to speech using ElevenLabs API with enhanced error handling
        """
        if not self.elevenlabs_api_key:
            print("❌ ElevenLabs API key not configured")
            logger.error("❌ ElevenLabs API key not configured")
            return None
            
        try:
            print(f"🔊 CREATING VOICE RESPONSE:")
            print(f"   🗣️ Text: {text[:100]}...")
            print(f"   🌍 Language: {language_code}")
            
            logger.info(f"🔊 Converting text to speech with ElevenLabs (language: {language_code})")
            
            # Get appropriate voice ID
            voice_id = self.ELEVENLABS_VOICES.get(language_code, self.ELEVENLABS_VOICES["hi-IN"])
            print(f"   🎭 Voice ID: {voice_id}")
            
            # Prepare the request
            url = f"{self.elevenlabs_base_url}/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            # Use ElevenLabs Turbo v2.5 for better Indian language support and speed
            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",  # Good balance of quality and speed
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5,
                    "use_speaker_boost": True
                }
            }
            
            print(f"   🌐 Making request to ElevenLabs...")
            
            # Make request to ElevenLabs
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            print(f"   📊 ElevenLabs Response: {response.status_code}")
            
            if response.status_code == 200:
                # Convert to base64 for transmission
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                print(f"   ✅ Voice generated: {len(audio_base64)} chars")
                logger.info(f"✅ Text converted to speech: {len(audio_base64)} chars")
                return audio_base64
            else:
                print(f"   ❌ ElevenLabs error: {response.status_code} - {response.text}")
                logger.error(f"❌ ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Voice generation error: {e}")
            logger.error(f"❌ Error in ElevenLabs text-to-speech: {e}")
            return None

# Global enhanced voice processor instance
enhanced_voice_processor = EnhancedVoiceProcessor()

def process_voice_message_from_web(audio_base64: str, farmer_language: str = "hindi") -> Optional[str]:
    """
    Process voice message from ADK Web interface (backward compatibility)
    
    Args:
        audio_base64: Base64 encoded audio from web browser
        farmer_language: Farmer's preferred language
        
    Returns:
        Transcribed text or None if failed
    """
    try:
        if not enhanced_voice_processor.speech_client:
            print("❌ Speech client not initialized")
            logger.error("❌ Speech client not initialized")
            return None
            
        print(f"\n🎤 PROCESSING WEB VOICE MESSAGE:")
        print(f"   🌍 Language: {farmer_language}")
        print(f"   📊 Audio Size: {len(audio_base64)} chars (base64)")
        
        # Decode base64 audio
        audio_data = base64.b64decode(audio_base64)
        language_code = enhanced_voice_processor.detect_language_from_context(farmer_language)
        
        # Configure recognition for web audio (typically WebM/Opus or MP3)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,  # Common web sample rate
            language_code=language_code,
            enable_automatic_punctuation=True,
            model="latest_short",
            use_enhanced=True,
        )
        
        audio = speech.RecognitionAudio(content=audio_data)
        
        # Perform speech recognition
        response = enhanced_voice_processor.speech_client.recognize(config=config, audio=audio)
        
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            print(f"   ✅ SUCCESS: {transcript}")
            print(f"   🎯 Confidence: {confidence:.2f}")
            logger.info(f"✅ Web speech recognized (confidence: {confidence:.2f}): {transcript[:50]}...")
            return transcript
        else:
            print("   ❌ No speech recognized in audio")
            logger.warning("⚠️ No speech recognized in web audio")
            return None
            
    except Exception as e:
        print(f"   ❌ Web speech recognition error: {e}")
        logger.error(f"❌ Error in web speech recognition: {e}")
        return None

def process_voice_message_from_whatsapp_enhanced(
    media_url: str, 
    auth_tuple: Tuple[str, str], 
    farmer_language: str = "hindi"
) -> Optional[str]:
    """
    ENHANCED: Process voice message from WhatsApp with better error handling
    
    Args:
        media_url: WhatsApp media URL for the voice message
        auth_tuple: Twilio authentication tuple (account_sid, auth_token)
        farmer_language: Farmer's preferred language
        
    Returns:
        Transcribed text or None if failed
    """
    language_code = enhanced_voice_processor.detect_language_from_context(farmer_language)
    return enhanced_voice_processor.enhanced_speech_to_text_from_url(media_url, auth_tuple, language_code)

def create_voice_response_for_farmer_enhanced(text: str, farmer_language: str = "hindi") -> Optional[str]:
    """
    ENHANCED: Create voice response in farmer's language using ElevenLabs
    
    Args:
        text: Text to convert to speech
        farmer_language: Farmer's preferred language
        
    Returns:
        Base64-encoded audio data or None if failed
    """
    language_code = enhanced_voice_processor.detect_language_from_context(farmer_language)
    return enhanced_voice_processor.text_to_speech_elevenlabs(text, language_code)

def check_voice_service_status_enhanced() -> Dict[str, Any]:
    """
    Enhanced status check for voice services
    """
    status = {
        "speech_to_text": {
            "provider": "Google Cloud Speech (Enhanced)",
            "status": "available" if enhanced_voice_processor.speech_client else "unavailable",
            "languages": list(enhanced_voice_processor.LANGUAGE_CODES.keys()),
            "configurations": 6  # Number of audio config attempts
        },
        "text_to_speech": {
            "provider": "ElevenLabs (Enhanced)",
            "status": "available" if enhanced_voice_processor.elevenlabs_api_key else "unavailable",
            "model": "eleven_turbo_v2_5",
            "languages": list(enhanced_voice_processor.ELEVENLABS_VOICES.keys())
        }
    }
    
    return status

# Backward compatibility - replace original functions
def process_voice_message_from_whatsapp(media_url: str, auth_tuple: Tuple[str, str], farmer_language: str = "hindi") -> Optional[str]:
    """Backward compatible function that uses enhanced processing"""
    return process_voice_message_from_whatsapp_enhanced(media_url, auth_tuple, farmer_language)

def create_voice_response_for_farmer(text: str, farmer_language: str = "hindi") -> Optional[str]:
    """Backward compatible function that uses enhanced processing"""
    return create_voice_response_for_farmer_enhanced(text, farmer_language)

def check_voice_service_status() -> Dict[str, Any]:
    """Backward compatible function that uses enhanced status check"""
    return check_voice_service_status_enhanced()

# Legacy functions for ADK integration
def process_voice_input(audio_data: str, source: str = "web", farmer_language: str = "hindi") -> Dict[str, Any]:
    """ADK Tool function to process voice input (enhanced)"""
    try:
        if source == "web":
            # For web, we'd need the base64 processing (not implemented in this fix)
            return {
                "success": False,
                "error": "Web voice processing not implemented in this enhanced version",
                "transcript": None
            }
        else:
            return {
                "success": False,
                "error": "WhatsApp processing requires media URL and auth credentials",
                "transcript": None
            }
    except Exception as e:
        logger.error(f"❌ Error in voice processing tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "transcript": None
        }

def generate_voice_response(text: str, farmer_language: str = "hindi") -> Dict[str, Any]:
    """ADK Tool function to generate voice response (enhanced)"""
    try:
        audio_base64 = create_voice_response_for_farmer_enhanced(text, farmer_language)
        
        if audio_base64:
            return {
                "success": True,
                "audio_data": audio_base64,
                "language": enhanced_voice_processor.detect_language_from_context(farmer_language),
                "format": "mp3",
                "encoding": "base64",
                "provider": "ElevenLabs Turbo v2.5 (Enhanced)",
                "estimated_cost": "~₹0.50"
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate voice response with ElevenLabs (Enhanced)",
                "audio_data": None
            }
            
    except Exception as e:
        logger.error(f"❌ Error in voice generation tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "audio_data": None
        }

if __name__ == "__main__":
    print("🔧 Enhanced Voice Processing Tool Loaded")
    print("✅ Multiple audio format support")
    print("✅ Better error handling")
    print("✅ Enhanced logging")
    print("✅ Backward compatibility maintained") 