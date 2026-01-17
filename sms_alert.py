from twilio.rest import Client
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

EMERGENCY_CONTACTS = [
    "+919595167618"
]

# Initialize Twilio Client (You can comment this out if you stop using it entirely)
# client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms_alert(lat, lon, event_type):
    """
    LOGS the emergency alert to the server console/database.
    Does NOT send an SMS (handled by Android App).
    """
    
    # 1. Get Timestamp
    timestamp = datetime.now().strftime("%I:%M %p")

    # 2. Build the Message (Just for logging purposes now)
    event_messages = {
        "USER_SOS": "SOS BUTTON PRESSED!",
        "AUTO_UNUSUAL_ACTIVITY": "UNUSUAL ACTIVITY DETECTED!",
        "MANUAL_SOS": "MANUAL SOS (Native App)",
        # Handle the specific tag we send from Android now:
        "MANUAL_SOS_SMS_SENT": "User sent SOS via Native SMS",
        "USER_SOS_SMS_SENT": "User sent SOS via Native SMS"
    }

    description = event_messages.get(event_type, f"Emergency: {event_type}")
    
    # 3. LOGGING ONLY (No SMS Sent)
    print("="*40)
    print(f"🚨 [SERVER LOG] EMERGENCY REPORTED")
    print(f"⏰ Time: {timestamp}")
    print(f"📍 Location: {lat}, {lon}")
    print(f"⚠️ Event: {description}")
    print("ℹ️ Action: SMS sending skipped (Handled by User's Mobile App)")
    print("="*40)

    # --- DISABLED TWILIO SECTION ---
    # The code below is commented out to save costs and prevent double SMS.
    """
    message_body = f"🚨 SAFE BAG ALERT: {description}\nLoc: http://maps.google.com/?q={lat},{lon}"
    
    for number in EMERGENCY_CONTACTS:
        try:
            msg = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE,
                to=number
            )
            print(f"Sent to {number}")
        except Exception as e:
            print(f"Error: {e}")
    """
    # -------------------------------
