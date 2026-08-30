import os
import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Session as DbSession, MissedSearch, Product, SessionStatusEnum
from apscheduler.schedulers.background import BackgroundScheduler

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

def send_twilio_sms(to_number: str, body: str):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not to_number:
        return
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = {
        "To": to_number,
        "From": TWILIO_FROM_NUMBER,
        "Body": body
    }
    try:
        requests.post(url, auth=auth, data=data)
    except Exception as e:
        print(f"Error sending SMS: {e}")

def run_proactive_outreach():
    db = SessionLocal()
    try:
        # 1. Recover abandoned carts
        abandoned_sessions = db.query(DbSession).filter(
            DbSession.status == 'abandoned',
            DbSession.phone_number.isnot(None)
        ).all()
        
        for sess in abandoned_sessions:
            if sess.cart_items:
                send_twilio_sms(
                    to_number=sess.phone_number,
                    body="Hi from Meera's Store! You left some items in your cart. Would you like to complete your order with a special 5% discount?"
                )
                sess.status = SessionStatusEnum.active # Mark active so we don't spam
                
        # 2. Back in stock / Custom generation notification
        missed = db.query(MissedSearch).join(DbSession).filter(DbSession.phone_number.isnot(None)).all()
        for m in missed:
            send_twilio_sms(
                to_number=m.session.phone_number,
                body=f"Great news! The '{m.search_query}' you were looking for is now available at Meera's Store. Reply here to check it out!"
            )
            db.delete(m)
            
        db.commit()
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_proactive_outreach, 'interval', minutes=10)
    scheduler.start()
