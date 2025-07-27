"""
WhatsApp Kisan Mitra Server - Twilio Integration

This server handles WhatsApp messages via Twilio and forwards them to the ADK API server.
"""

import asyncio
import logging
import os
import requests
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response
from urllib.parse import quote_plus
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Kisan Mitra", version="1.0.0")

# Configuration
ADK_API_URL = "http://localhost:8001"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

@app.on_event("startup")
async def startup_event():
    """Initialize the WhatsApp server"""
    logger.info("📱 Starting WhatsApp Kisan Mitra Server...")
    logger.info(f"🔗 ADK API URL: {ADK_API_URL}")
    
    # Check ADK API connectivity
    try:
        response = requests.get(f"{ADK_API_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ ADK API server is reachable")
        else:
            logger.warning(f"⚠️ ADK API server returned status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Cannot reach ADK API server: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "📱 WhatsApp Kisan Mitra Server is running",
        "status": "healthy",
        "adk_api": ADK_API_URL
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    adk_status = "unknown"
    try:
        response = requests.get(f"{ADK_API_URL}/health", timeout=5)
        adk_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        adk_status = "unreachable"
    
    return {
        "status": "healthy",
        "service": "WhatsApp Kisan Mitra",
        "version": "1.0.0",
        "adk_api_status": adk_status,
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
    }

async def call_adk_api(message: str, phone_number: str = None, image_data: str = None, image_mime_type: str = None):
    """Call the ADK API server"""
    try:
        app_name = "kisan_mitra"
        user_id = phone_number or "default_user"
        
        # First, create or ensure session exists
        logger.info(f"🔄 Creating session for user: {user_id}")
        session_response = requests.post(
            f"{ADK_API_URL}/apps/{app_name}/users/{user_id}/sessions",
            json={},
            timeout=10
        )
        
        if session_response.status_code not in [200, 201]:
            logger.warning(f"⚠️ Session creation failed: {session_response.status_code}")
            return "माफ करें, सत्र बनाने में समस्या है।"
        
        # Get the actual session ID from the response
        session_data = session_response.json()
        session_id = session_data.get("id")
        
        if not session_id:
            logger.error("❌ No session ID returned from session creation")
            return "माफ करें, सत्र की पहचान नहीं मिली।"
        
        logger.info(f"✅ Session created: {session_id}")
        
        # Format the payload for ADK API
        payload = {
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [
                    {
                        "text": message
                    }
                ]
            }
        }
        
        # Add image data if present
        if image_data and image_mime_type:
            logger.info(f"📸 Adding image to payload: {image_mime_type}")
            payload["newMessage"]["parts"].append({
                "inlineData": {
                    "mimeType": image_mime_type,
                    "data": image_data
                }
            })
            
            # Update the text message to indicate image is included
            if payload["newMessage"]["parts"][0]["text"]:
                payload["newMessage"]["parts"][0]["text"] += "\n\n[मैंने एक तस्वीर भेजी है, कृपया इसका विश्लेषण करें]"
            else:
                payload["newMessage"]["parts"][0]["text"] = "कृपया इस तस्वीर का विश्लेषण करें और मुझे बताएं कि इसमें क्या समस्या है।"
        
        logger.info(f"🔄 Calling ADK API for message: {message[:50]}...")
        
        response = requests.post(
            f"{ADK_API_URL}/run",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # ADK API returns a list of events, we need the last event with text
            if isinstance(result, list) and len(result) > 0:
                # Look through events in reverse order to find the last text response
                for event in reversed(result):
                    if "content" in event and event["content"]:
                        content = event["content"]
                        if "parts" in content:
                            for part in content["parts"]:
                                if "text" in part and part["text"].strip():
                                    logger.info(f"✅ ADK API response: {len(part['text'])} characters")
                                    return part["text"]
            
            # Fallback for non-list responses
            if isinstance(result, dict):
                # Extract the text response from ADK API response
                if "content" in result and result["content"]:
                    # Look for text content in the response parts
                    for part in result["content"].get("parts", []):
                        if "text" in part:
                            logger.info(f"✅ ADK API response: {len(part['text'])} characters")
                            return part["text"]
                
                # Fallback: check for direct text field
                if "text" in result:
                    return result["text"]
                    
                # Check if it's in finalResponse
                if "finalResponse" in result and result["finalResponse"]:
                    for part in result["finalResponse"].get("parts", []):
                        if "text" in part:
                            logger.info(f"✅ ADK API response: {len(part['text'])} characters")
                            return part["text"]
            
            logger.error(f"❌ No text found in ADK API response")
            return "माफ करें, सर्वर से कोई उत्तर नहीं मिला।"
        else:
            logger.error(f"❌ ADK API HTTP error: {response.status_code} - {response.text}")
            return "माफ करें, सर्वर से संपर्क में समस्या है।"
            
    except requests.exceptions.Timeout:
        logger.error("⏰ ADK API timeout")
        return "माफ करें, प्रतिक्रिया में देरी हो रही है। कृपया फिर से कोशिश करें।"
    except Exception as e:
        logger.error(f"❌ Error calling ADK API: {e}")
        return "माफ करें, तकनीकी समस्या के कारण मैं अभी आपकी मदद नहीं कर सकता।"

def format_whatsapp_response(text: str) -> str:
    """Format response for WhatsApp (handle length limits)"""
    # WhatsApp has a 1600 character limit per message
    if len(text) <= 1600:
        return text
    
    # Split long messages
    parts = []
    current_part = ""
    sentences = text.split('। ')
    
    for sentence in sentences:
        if len(current_part + sentence + '। ') <= 1500:  # Leave some buffer
            current_part += sentence + '। '
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = sentence + '। '
    
    if current_part:
        parts.append(current_part.strip())
    
    # Return first part with indication of more content
    if len(parts) > 1:
        return parts[0] + "\n\n📱 अधिक जानकारी के लिए कृपया दोबारा पूछें।"
    
    return parts[0] if parts else text[:1500]

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    MessageSid: Optional[str] = Form(None),
    NumMedia: Optional[str] = Form("0"),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):
    """Handle incoming WhatsApp messages from Twilio"""
    try:
        logger.info(f"📱 Received WhatsApp message from {From}: {Body[:50]}...")
        logger.info(f"🔍 DEBUG: NumMedia={NumMedia}, MediaUrl0={MediaUrl0}, MediaContentType0={MediaContentType0}")
        
        # Extract phone number
        phone_number = From.replace("whatsapp:", "")
        
        # Handle media (images)
        image_data = None
        image_mime_type = None
        
        if NumMedia and int(NumMedia) > 0 and MediaUrl0:
            try:
                logger.info(f"📸 Processing media: {MediaContentType0}")
                logger.info(f"📸 Media URL: {MediaUrl0}")
                
                # Download the image with Twilio authentication
                auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                media_response = requests.get(MediaUrl0, auth=auth, timeout=10)
                if media_response.status_code == 200:
                    # Convert to base64
                    image_data = base64.b64encode(media_response.content).decode('utf-8')
                    image_mime_type = MediaContentType0
                    logger.info(f"✅ Image processed successfully - {len(image_data)} chars, type: {image_mime_type}")
                else:
                    logger.warning(f"⚠️ Failed to download media: {media_response.status_code} - {media_response.text}")
            except Exception as e:
                logger.error(f"❌ Error processing media: {e}")
        else:
            logger.info(f"📝 No media detected - NumMedia: {NumMedia}")
        
        # Get response from ADK API
        agent_response = await call_adk_api(
            message=Body,
            phone_number=phone_number,
            image_data=image_data,
            image_mime_type=image_mime_type
        )
        
        # Format response for WhatsApp
        formatted_response = format_whatsapp_response(agent_response)
        
        # Create TwiML response
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{formatted_response}</Message>
</Response>"""
        
        logger.info(f"📤 Sending response: {len(formatted_response)} characters")
        
        return Response(
            content=twiml_response,
            media_type="application/xml",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error in webhook: {e}")
        
        # Return error message in TwiML format
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>माफ करें, तकनीकी समस्या के कारण मैं अभी आपकी मदद नहीं कर सकता।</Message>
</Response>"""
        
        return Response(
            content=error_twiml,
            media_type="application/xml",
            status_code=200
        )

@app.post("/debug/webhook")
async def debug_webhook(request: Request):
    """Debug endpoint to see all webhook data"""
    try:
        form_data = await request.form()
        body = await request.body()
        
        logger.info("🔍 DEBUG WEBHOOK DATA:")
        logger.info(f"Form data: {dict(form_data)}")
        logger.info(f"Raw body: {body.decode('utf-8', errors='ignore')}")
        
        return {"status": "debug", "form_data": dict(form_data), "body": body.decode('utf-8', errors='ignore')}
        
    except Exception as e:
        logger.error(f"❌ Debug webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/test/message")
async def test_message(message: str, phone: str = "+919876543210"):
    """Test endpoint to simulate WhatsApp message"""
    try:
        logger.info(f"🧪 Test message: {message}")
        
        response = await call_adk_api(message=message, phone_number=phone)
        formatted_response = format_whatsapp_response(response)
        
        return {
            "original_message": message,
            "agent_response": response,
            "formatted_response": formatted_response,
            "success": True
        }
    except Exception as e:
        return {
            "original_message": message,
            "error": str(e),
            "success": False
        }

if __name__ == "__main__":
    import uvicorn
    
    # Check for required environment variables
    if not TWILIO_ACCOUNT_SID:
        logger.warning("⚠️ TWILIO_ACCOUNT_SID not configured")
    if not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️ TWILIO_AUTH_TOKEN not configured")
    
    logger.info("📱 Starting WhatsApp Kisan Mitra Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 