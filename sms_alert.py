from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

EMERGENCY_CONTACTS = [
    "+919595167618"
]

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms_alert(lat, lon, event_type):
    message_body = f"""🚨 SAFE BAG ALERT 🚨
Event: {event_type}
Location: https://maps.google.com/?q={lat},{lon}
"""

    for number in EMERGENCY_CONTACTS:
        try:
            msg = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE,
                to=number
            )
            print(f"SMS sent to {number} | SID={msg.sid}")
        except Exception as e:
            print(f"Failed to send SMS to {number}: {e}")
