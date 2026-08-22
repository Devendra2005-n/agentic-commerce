from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine, Base
from app.payments import razorpay
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Growth & Trust Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dashboard APIs ---

@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    try:
        # Calculate stats from raw tables dynamically
        sessions_count = db.execute(text("SELECT COUNT(*) FROM sessions")).scalar() or 0
        orders_count = db.execute(text("SELECT COUNT(DISTINCT razorpay_order_id) FROM audit_events WHERE status = 'captured'")).scalar() or 0
        revenue = db.execute(text("SELECT SUM((detail->>'amount_paise')::int) FROM audit_events WHERE status = 'captured'")).scalar() or 0
        rejections = db.execute(text("SELECT COUNT(*) FROM decisions WHERE decision = 'rejected'")).scalar() or 0
        
        return {
            "sessions": sessions_count,
            "orders": orders_count,
            "revenue_paise": revenue,
            "guardrail_rejections": rejections
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {"sessions": 0, "orders": 0, "revenue_paise": 0, "guardrail_rejections": 0}

@app.get("/api/audit/timeline/{session_id}")
def get_session_timeline(session_id: str, db: Session = Depends(get_db)):
    try:
        results = db.execute(
            text("SELECT * FROM v_session_timeline WHERE session_id = :sid"),
            {"sid": session_id}
        ).mappings().all()
        return [dict(r) for r in results]
    except Exception:
        return []

# --- Chat/Agent APIs ---
from app.orchestrator.agent import call_llm
import firebase_admin
from firebase_admin import credentials, auth
import os

# Initialize Firebase Admin
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase-service-account.json')
try:
    if not firebase_admin._apps:
        firebase_env = os.getenv('FIREBASE_SERVICE_ACCOUNT')
        if firebase_env:
            cred_dict = json.loads(firebase_env)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f'Firebase initialization error: {e}')

@app.post("/api/chat")
def handle_chat_message(request: dict, db: Session = Depends(get_db)):
    user_msg = request.get("message", "")
    buyer_ref = request.get("buyer_ref", "anonymous")
    
    # Try to verify as Firebase ID Token first
    try:
        if buyer_ref and len(buyer_ref) > 100: # JWT tokens are long
            decoded_token = auth.verify_id_token(buyer_ref)
            # Use email if available, otherwise phone, otherwise uid
            buyer_ref = decoded_token.get("email") or decoded_token.get("phone_number") or decoded_token.get("uid")
    except Exception as e:
        print(f"Token verification failed: {e}")
        # Continue with raw buyer_ref (for testing/mock purposes)
    
    # Route through the True AI Orchestrator
    try:
        response = call_llm(db, user_msg, buyer_ref)
        return response
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"type": "text", "text": f"Agent error: {e}"}

# --- Webhooks & Payments ---

@app.post("/api/orders")
def create_checkout_order(request: dict, db: Session = Depends(get_db)):
    raw_amount = request.get("amount_paise")
    if not raw_amount:
        raise HTTPException(status_code=400, detail="amount_paise is required")
        
    try:
        # Razorpay strictly requires an integer
        amount = int(float(raw_amount))
        # Generate an order in Razorpay using the SDK
        order = razorpay.create_order(db, session_id="sess_a1b2", cart_total_paise=amount, decision_id="dec_1")
        return {"order_id": order["id"]}
    except Exception as e:
        print(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    is_valid = await razorpay.verify_webhook_signature(request, db)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode('utf-8'))
        event_type = payload.get('event')
        razorpay.handle_webhook_event(db, event_type, payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}



