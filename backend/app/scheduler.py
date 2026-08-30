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

def monitor_inventory():
    from app.models import PurchaseOrder, AuditEvent
    import uuid
    db = SessionLocal()
    try:
        low_stock_products = db.query(Product).filter(Product.stock_qty < 10).all()
        for product in low_stock_products:
            # Check if PO already exists
            existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.sku == product.sku, PurchaseOrder.status == 'sent_to_supplier').first()
            if not existing_po:
                order_qty = 50
                negotiated_price = int(product.price_paise * 0.4) # Negotiate 60% margin
                po = PurchaseOrder(sku=product.sku, qty_ordered=order_qty, negotiated_price_paise=negotiated_price)
                db.add(po)
                
                # Mock audit
                # Just print for now or add to audit events if we had a global session
                print(f"[Autonomous Restock Agent] Issued PO for {order_qty} units of {product.sku} at {negotiated_price/100} INR each.")
        db.commit()
    finally:
        db.close()

def competitive_pricing_agent():
    import random
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        for product in products:
            # Mock competitor web scrape: 10% chance competitor dropped price
            if random.random() < 0.10:
                competitor_price = int(product.price_paise * 0.95) # Competitor is 5% cheaper
                new_price = int(competitor_price * 0.99) # We beat them by 1%
                min_price = int(product.price_paise * 0.70) # 30% max overall drop guardrail
                
                if new_price >= min_price:
                    print(f"[Pricing Agent] Competitor dropped price for {product.sku}. Adjusting from {product.price_paise/100} to {new_price/100}.")
                    product.price_paise = new_price
        db.commit()
    finally:
        db.close()

def marketing_agent():
    from app.models import OutboundCampaign, CartItem
    from sqlalchemy.orm import aliased
    db = SessionLocal()
    try:
        # Find products with stock > 20 and 0 sales
        all_prods = db.query(Product).filter(Product.stock_qty > 20).all()
        sold_skus = [c.sku for c in db.query(CartItem.sku).distinct().all()]
        stale_prods = [p for p in all_prods if p.sku not in sold_skus]
        
        # Get users with phone numbers
        users = db.query(DbSession.phone_number).filter(DbSession.phone_number.isnot(None)).distinct().all()
        
        for p in stale_prods:
            for user in users:
                phone = user[0]
                already_sent = db.query(OutboundCampaign).filter_by(sku=p.sku, target_phone=phone).first()
                if not already_sent:
                    msg = f"Flash Sale! 🌟 Get our premium {p.title} for just ₹{int(p.price_paise/100)}. Reply YES to order instantly via Meera's Store!"
                    send_twilio_sms(phone, msg)
                    db.add(OutboundCampaign(sku=p.sku, message_body=msg, target_phone=phone))
                    print(f"[Marketing Agent] Sent campaign for {p.sku} to {phone}")
        db.commit()
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_proactive_outreach, 'interval', minutes=10)
    scheduler.add_job(monitor_inventory, 'interval', minutes=30)
    scheduler.add_job(competitive_pricing_agent, 'interval', minutes=15)
    scheduler.add_job(marketing_agent, 'interval', minutes=1440) # daily
    scheduler.start()
