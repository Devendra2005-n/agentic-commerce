from fastapi import FastAPI, Depends, Request, HTTPException, Form, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
from app.database import get_db
from app.catalog.service import search_catalog
from app.payments.service import initiate_checkout, handle_razorpay_webhook
from app.payments.razorpay_client import verify_webhook_signature, get_decrypted_secret
from app.models import MerchantConfig
from app.orchestrator.agent import process_chat

from typing import Optional

class ChatRequest(BaseModel):
    message: str
    image_base64: Optional[str] = None

app = FastAPI(title="Growth & Trust Agent API")

@app.on_event("startup")
def startup_event():
    from app.scheduler import start_scheduler
    start_scheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/v1/agent/catalog")
def get_catalog(query: str, max_price_paise: int = None, tags: str = None, db: Session = Depends(get_db)):
    tag_list = tags.split(",") if tags else None
    results = search_catalog(db, query, max_price_paise, tag_list)
    return {"data": results}

from app.models import MerchantConfig, Session as DbSession, ActorTypeEnum

class SessionRequest(BaseModel):
    phone_number: str = None

@app.post("/v1/sessions")
def create_session(req: SessionRequest = None, db: Session = Depends(get_db)):
    merchant = db.query(MerchantConfig).first()
    if not merchant:
        raise HTTPException(status_code=500, detail="No merchant configured")
        
    if req and req.phone_number:
        existing = db.query(DbSession).filter(DbSession.phone_number == req.phone_number, DbSession.status == 'active').first()
        if existing:
            return {"session_id": existing.session_id, "resumed": True}
            
    session_db = DbSession(
        merchant_id=merchant.merchant_id,
        actor_type=ActorTypeEnum.human,
        phone_number=req.phone_number if req else None
    )
    db.add(session_db)
    db.commit()
    db.refresh(session_db)
    return {"session_id": session_db.session_id, "resumed": False}

@app.post("/v1/checkout/{session_id}")
def checkout(session_id: uuid.UUID, db: Session = Depends(get_db)):
    return initiate_checkout(db, session_id)

@app.post("/v1/chat/{session_id}")
def chat(session_id: uuid.UUID, req: ChatRequest, db: Session = Depends(get_db)):
    return process_chat(db, session_id, req.message, req.image_base64)

@app.post("/v1/webhooks/razorpay/{merchant_id}")
async def razorpay_webhook(merchant_id: str, request: Request, db: Session = Depends(get_db)):
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    signature = request.headers.get('X-Razorpay-Signature')
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    merchant = db.query(MerchantConfig).filter(MerchantConfig.merchant_id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    import razorpay
    client = razorpay.Client(auth=("dummy", "dummy")) # only needed for utility
    secret = get_decrypted_secret(merchant.webhook_secret_enc)
    
    if not verify_webhook_signature(client, body_str, signature, secret):
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    payload = await request.json()
    return handle_razorpay_webhook(db, payload, merchant_id)

# --- ADMIN ENDPOINTS ---

from app.models import Product

class ConfigUpdateRequest(BaseModel):
    max_order_paise: int
    max_discount_pct: float

@app.get("/v1/admin/config")
def get_admin_config(db: Session = Depends(get_db)):
    merchant = db.query(MerchantConfig).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No config found")
    return {
        "max_order_paise": merchant.max_order_paise,
        "max_discount_pct": float(merchant.max_discount_pct)
    }

@app.post("/v1/admin/config")
def update_admin_config(req: ConfigUpdateRequest, db: Session = Depends(get_db)):
    merchant = db.query(MerchantConfig).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No config found")
    merchant.max_order_paise = req.max_order_paise
    merchant.max_discount_pct = req.max_discount_pct
    db.commit()
    return {"status": "success"}

@app.get("/v1/admin/catalog")
def get_full_catalog(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return {"data": [
        {
            "sku": p.sku,
            "title": p.title,
            "price_paise": p.price_paise,
            "stock_qty": p.stock_qty,
            "category": p.category
        } for p in products
    ]}

@app.post("/v1/twilio/webhook")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    from app.models import MerchantConfig, Session as DbSession, ActorTypeEnum
    merchant = db.query(MerchantConfig).first()
    
    parsed_phone = From.replace("whatsapp:", "").strip()
    
    sess = db.query(DbSession).filter(
        (DbSession.phone_number == parsed_phone) | (DbSession.buyer_ref == From),
        DbSession.status == 'active'
    ).first()
    
    if not sess:
        sess = DbSession(merchant_id=merchant.merchant_id, actor_type=ActorTypeEnum.human, buyer_ref=From, phone_number=parsed_phone)
        db.add(sess)
        db.commit()
        db.refresh(sess)
        
    result = process_chat(db, sess.session_id, Body)
    agent_msg = result.get('content', "I didn't quite get that.")
    
    if result.get('data') and 'payment_link_url' in result['data']:
        agent_msg += f"\nPay here: {result['data']['payment_link_url']}"
        
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{agent_msg}</Message>
</Response>"""
    return Response(content=twiml_response, media_type="application/xml")

@app.get("/v1/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    from app.models import Session as DbSession, CartItem, Product, MissedSearch
    from sqlalchemy import func
    
    total_sessions = db.query(func.count(DbSession.session_id)).scalar() or 0
    checked_out = db.query(func.count(DbSession.session_id)).filter(DbSession.status == 'checked_out').scalar() or 0
    win_rate = (checked_out / total_sessions * 100) if total_sessions > 0 else 0
    
    # Negotiation spread: average of (Product.price_paise - CartItem.price_at_add_paise)
    items = db.query(CartItem.price_at_add_paise, Product.price_paise).join(Product, CartItem.sku == Product.sku).all()
    spreads = [(p - c) for c, p in items if p > c]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0
    
    # Missed searches
    missed = db.query(MissedSearch.search_query, func.count(MissedSearch.id).label('count')).group_by(MissedSearch.search_query).order_by(func.count(MissedSearch.id).desc()).limit(5).all()
    missed_list = [{"query": m[0], "count": m[1]} for m in missed]
    
    return {
        "win_rate_pct": round(win_rate, 2),
        "avg_negotiation_spread_paise": round(avg_spread, 2),
        "total_sessions": total_sessions,
        "checked_out_sessions": checked_out,
        "top_missed_searches": missed_list
    }

@app.get("/v1/storefront/config")
def get_storefront_config(db: Session = Depends(get_db)):
    from app.models import StorefrontConfig
    config = db.query(StorefrontConfig).filter_by(is_active=True).first()
    if not config:
        return {"theme_color": "#ef4444", "welcome_message": "Hi! I can help you find something from Meera's Store. What are you looking for?"}
    return {"theme_color": config.theme_color, "welcome_message": config.welcome_message}

@app.get("/v1/admin/social")
def get_social_feed(db: Session = Depends(get_db)):
    from app.models import SocialFeed
    posts = db.query(SocialFeed).order_by(SocialFeed.created_at.desc()).limit(20).all()
    return [{"post_id": str(p.post_id), "image_url": p.image_url, "caption": p.caption, "platform": p.platform, "likes_count": p.likes_count, "comments_count": p.comments_count, "shares_count": p.shares_count, "created_at": p.created_at.isoformat()} for p in posts]

@app.post("/v1/admin/social/trigger")
def trigger_social_agent(background_tasks: BackgroundTasks):
    from app.scheduler import social_media_agent
    background_tasks.add_task(social_media_agent)
    return {"status": "triggered"}

@app.delete("/v1/admin/social/{post_id}")
def delete_social_post(post_id: str, db: Session = Depends(get_db)):
    from app.models import SocialFeed
    post = db.query(SocialFeed).filter(SocialFeed.post_id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
        return {"status": "deleted"}
    return {"status": "not_found"}

@app.get("/v1/admin/report")
def get_executive_report(db: Session = Depends(get_db)):
    from app.models import ExecutiveReport
    report = db.query(ExecutiveReport).order_by(ExecutiveReport.created_at.desc()).first()
    if not report:
        return {"report_markdown": "No report generated yet. The Sentiment Agent will run tonight."}
    return {"report_markdown": report.report_markdown, "generated_at": report.created_at.isoformat()}

