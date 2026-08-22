import razorpay
import json
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models import MerchantConfig, AuditEvent
from typing import Dict, Any

def get_razorpay_client(db: Session) -> razorpay.Client:
    config = db.query(MerchantConfig).first()
    if not config:
        raise ValueError("Merchant config not found")
    # In a real system, razorpay_key_secret_enc would be decrypted here.
    # For MVP, assuming it's stored directly or decrypted before this step.
    # We will use dummy decryption for the sake of the skeleton.
    key_secret = config.razorpay_key_secret_enc.decode('utf-8') if config.razorpay_key_secret_enc else ""
    client = razorpay.Client(auth=(config.razorpay_key_id, key_secret))
    return client

def create_order(db: Session, session_id: str, cart_total_paise: int, decision_id: str) -> Dict[str, Any]:
    client = get_razorpay_client(db)
    
    order_data = {
        "amount": cart_total_paise,
        "currency": "INR",
        "receipt": f"session_{session_id}",
        "notes": {
            "session_id": str(session_id),
            "guardrail_decision_id": str(decision_id),
        }
    }
    # Note: payment_capture is omitted per TRD §7.1
    order = client.order.create(data=order_data)
    return order

def create_payment_link(db: Session, order_id: str, cart_total_paise: int, session_id: str, base_url: str) -> Dict[str, Any]:
    client = get_razorpay_client(db)
    
    link_data = {
        "amount": cart_total_paise,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": order_id,
        "notes": {"session_id": str(session_id)},
        "callback_url": f"{base_url}/checkout/callback",
        "callback_method": "get"
    }
    
    link = client.payment_link.create(data=link_data)
    return link

async def verify_webhook_signature(request: Request, db: Session) -> bool:
    config = db.query(MerchantConfig).first()
    if not config:
        raise HTTPException(status_code=500, detail="Merchant config missing")
        
    webhook_secret = config.webhook_secret_enc.decode('utf-8') if config.webhook_secret_enc else ""
    
    # Razorpay requires the raw body for signature verification
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    if not signature:
        return False
        
    client = get_razorpay_client(db)
    try:
        client.utility.verify_webhook_signature(
            raw_body.decode('utf-8'),
            signature,
            webhook_secret
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False

def handle_webhook_event(db: Session, event_type: str, payload: Dict[str, Any]):
    # Parse event based on TRD §7.4
    if event_type not in ['payment.captured', 'payment.failed', 'order.paid']:
        return
        
    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    razorpay_payment_id = payment_entity.get('id')
    razorpay_order_id = payment_entity.get('order_id')
    notes = payment_entity.get('notes', {})
    session_id = notes.get('session_id')
    
    if not session_id:
        return # Cannot tie back to our session
        
    # Idempotency check: if already captured, ignore
    existing = db.query(AuditEvent).filter(
        AuditEvent.razorpay_payment_id == razorpay_payment_id,
        AuditEvent.status == 'captured'
    ).first()
    
    if existing:
        return
        
    status_map = {
        'payment.captured': 'captured',
        'payment.failed': 'failed',
        'order.paid': 'captured'
    }
    
    new_status = status_map.get(event_type)
    
    if new_status:
        audit_event = AuditEvent(
            session_id=session_id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            status=new_status,
            detail={"webhook_event": event_type, "amount_paise": payment_entity.get('amount')}
        )
        db.add(audit_event)
        db.commit()
