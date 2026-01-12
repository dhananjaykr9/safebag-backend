from twilio.rest import Client
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration from .env file
ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# List of emergency contacts
EMERGENCY_CONTACTS = [
    "+919595167618"
]

# Initialize Twilio Client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms_alert(lat, lon, event_type):
    """
    Sends a high-priority SMS alert via Twilio based on the event type.
    """
    
    # 1. Human-readable event mapping
    event_messages = {
        "USER_SOS": "SOS BUTTON PRESSED! I am in immediate danger and need help.",
        "AUTO_UNUSUAL_ACTIVITY": "UNUSUAL ACTIVITY DETECTED! My handbag has detected potential theft or a fall.",
        "MANUAL_SOS": "MANUAL SOS triggered from my smartphone app.",
        "MOBILE_APP": "SOS triggered directly from the mobile interface."
    }

    # Default message if event_type doesn't match the dictionary
    description = event_messages.get(event_type, f"Emergency Alert detected: {event_type}")
    
    # Get current time for the message
    timestamp = datetime.now().strftime("%I:%M %p")

    # 2. Build the Message Body
    # Using the standard Google Maps URL format for universal compatibility
    message_body = f"""🚨 SAFE BAG: EMERGENCY 🚨

{description}

Time: {timestamp}
📍 My Live Location:
https://www.google.com/maps?q={lat},{lon}
"""
    # 3. Send to all contacts
    for number in EMERGENCY_CONTACTS:
        try:
            msg = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE,
                to=number
            )
            print(f"[{timestamp}] SMS sent to {number} | SID: {msg.sid} | Type: {event_type}")
        except Exception as e:
            print(f"[{timestamp}] Failed to send SMS to {number}: {e}")
