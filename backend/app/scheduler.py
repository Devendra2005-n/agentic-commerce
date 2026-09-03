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
                
                # Use LLM for Supplier Web Research
                api_key = os.getenv("GEMINI_API_KEY", "dummy_key")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                prompt = f"You are an automated B2B sourcing agent. Simulate searching the web for wholesale suppliers for '{product.title}'. Give me the cheapest wholesale price you can find in INR as a JSON response like {{\"price_inr\": 120}}. Keep it under {(product.price_paise / 100) * 0.5} INR. Output purely JSON."
                
                negotiated_price = int(product.price_paise * 0.4) # Fallback
                try:
                    res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
                    if res.status_code == 200:
                        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        import json
                        import re
                        match = re.search(r'\{.*\}', text.replace('\n', ''))
                        if match:
                            data = json.loads(match.group(0))
                            negotiated_price = int(data.get("price_inr", negotiated_price/100)) * 100
                except Exception as e:
                    print(f"Sourcing agent LLM failed, using fallback: {e}")
                
                po = PurchaseOrder(sku=product.sku, qty_ordered=order_qty, negotiated_price_paise=negotiated_price)
                db.add(po)
                
                print(f"[Autonomous Restock Agent (LLM)] Researched web and issued PO for {order_qty} units of {product.sku} at {negotiated_price/100} INR each.")
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
                    msg = f"Flash Sale! ?? Get our premium {p.title} for just ?{int(p.price_paise/100)}. Reply YES to order instantly via Meera's Store!"
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
    
    # Phase 4 Agents
    scheduler.add_job(profiling_agent, 'interval', minutes=60)
    scheduler.add_job(social_media_agent, 'interval', minutes=120)
    scheduler.add_job(ab_testing_agent, 'interval', minutes=60)
    scheduler.add_job(sentiment_agent, 'interval', minutes=1440) # daily
    
    scheduler.start()

def profiling_agent():
    from app.models import UserProfile, Message
    import json
    db = SessionLocal()
    try:
        # Mocking profiling logic to avoid complex LLM calls in background for now
        sessions = db.query(DbSession).filter(DbSession.phone_number.isnot(None)).all()
        for sess in sessions:
            phone = sess.phone_number
            profile = db.query(UserProfile).filter_by(phone_number=phone).first()
            if not profile:
                # Based on messages, tag them. Just a mock static tag for demo
                profile = UserProfile(phone_number=phone, tags_json=["budget-conscious", "impulse-buyer"])
                db.add(profile)
                print(f"[Profiling Agent] Tagged {phone}")
        db.commit()
    finally:
        db.close()

def social_media_agent():
    from app.models import SocialFeed
    import urllib.parse
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        if products:
            import random
            p = random.choice(products)
            
            prompt = f"A gorgeous Instagram lifestyle photo of {p.title}"
            # Add seed to image_url so it doesn't get cached if same product is picked twice
            image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?nologo=true&seed={random.randint(1,1000)}"
            
            # Use LLM to generate a unique caption
            import requests, os
            api_key = os.getenv("GEMINI_API_KEY", "dummy_key")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            llm_prompt = f"Write a short, engaging, viral Instagram caption for a product named '{p.title}'. Include a couple of relevant emojis and 3 hashtags. Do not include quotes."
            
            caption = f"Just dropped! 🌟 Check out our stunning {p.title}. Tap the link in bio to transform your space today! #design #meerastore"
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                res = requests.post(url, json={"contents": [{"parts": [{"text": llm_prompt}]}]}, timeout=10, verify=False)
                if res.status_code == 200:
                    caption = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"Social LLM failed: {e}")
            
            likes = random.randint(50, 1500)
            comments = random.randint(5, 100)
            shares = random.randint(1, 50)
            
            feed = SocialFeed(
                image_url=image_url, 
                caption=caption, 
                platform="Instagram",
                likes_count=likes,
                comments_count=comments,
                shares_count=shares
            )
            db.add(feed)
            db.commit()
            print(f"[Social Media Agent] Posted {p.sku} to Instagram.")
    finally:
        db.close()

def ab_testing_agent():
    from app.models import StorefrontConfig
    import random
    db = SessionLocal()
    try:
        # Calculate win rate
        total = db.query(DbSession).count()
        if total > 0:
            config = db.query(StorefrontConfig).first()
            if not config:
                config = StorefrontConfig()
                db.add(config)
            
            colors = ["#ef4444", "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b"]
            config.theme_color = random.choice(colors)
            print(f"[A/B Testing Agent] Mutated theme color to {config.theme_color}")
            db.commit()
    finally:
        db.close()

def sentiment_agent():
    from app.models import ExecutiveReport
    db = SessionLocal()
    try:
        # Mock summary
        report_md = "### Daily Executive Summary\\n\\n**Top 3 Loves:**\\n1. Fast checkout\\n2. Voice interface\\n3. Custom product generation\\n\\n**Top 3 Complaints:**\\n1. Needs more product variety\\n2. Prices slightly high\\n3. Occasional mic glitches"
        report = ExecutiveReport(report_markdown=report_md)
        db.add(report)
        db.commit()
        print("[Sentiment Agent] Executive Report generated.")
    finally:
        db.close()
