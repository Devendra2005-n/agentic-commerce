from sqlalchemy.orm import Session
from app.models import MerchantConfig, Session as DbSession, CartItem, AuditEvent, AuditStatusEnum
from app.payments.razorpay_client import get_razorpay_client, create_rzp_order, create_rzp_payment_link, get_decrypted_secret
from fastapi import HTTPException
import uuid

def initiate_checkout(db: Session, session_id: uuid.UUID):
    # Fetch session and cart
    session_db = db.query(DbSession).filter(DbSession.session_id == session_id).first()
    if not session_db:
        raise HTTPException(status_code=404, detail="Session not found")
        
    merchant = db.query(MerchantConfig).filter(MerchantConfig.merchant_id == session_db.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id, CartItem.removed_at == None).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
        
    amount_paise = sum(item.price_at_add_paise * item.qty for item in cart_items)
    
    # Init Razorpay Client
    client = get_razorpay_client(merchant.razorpay_key_id, merchant.razorpay_key_secret_enc)
    
    # Create Razorpay Order
    receipt_id = f"receipt_{str(session_id)[:8]}"
    notes = {"session_id": str(session_id)}
    
    order = create_rzp_order(client, amount_paise, receipt_id, notes)
    
    # Create Payment Link (for the buyer to actually pay)
    plink = create_rzp_payment_link(
        client, 
        amount_paise, 
        reference_id=order['id'], 
        description=f"Order from {merchant.display_name}", 
        notes=notes
    )
    
    # Create Audit Event (Awaiting Payment)
    audit = AuditEvent(
        session_id=session_id,
        razorpay_order_id=order['id'],
        status=AuditStatusEnum.awaiting_payment,
        detail={
            "amount_paise": amount_paise,
            "payment_link_id": plink['id'],
            "payment_link_url": plink['short_url']
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    
    return {
        "order_id": order['id'],
        "payment_link_url": plink['short_url'],
        "audit_event_id": audit.event_id,
        "razorpay_key_id": merchant.razorpay_key_id,
        "amount_paise": amount_paise
    }

def handle_razorpay_webhook(db: Session, payload: dict, merchant_id: str):
    merchant = db.query(MerchantConfig).filter(MerchantConfig.merchant_id == merchant_id).first()
    if not merchant:
        raise ValueError("Merchant not found")
        
    event_type = payload.get('event')
    
    if event_type == 'payment.captured':
        payment = payload['payload']['payment']['entity']
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        notes = payment.get('notes', {})
        session_id_str = notes.get('session_id')
        
        if not order_id or not session_id_str:
            return {"status": "ignored", "reason": "Missing order_id or session_id in notes"}
            
        try:
            session_id = uuid.UUID(session_id_str)
        except ValueError:
            return {"status": "ignored", "reason": "Invalid session_id format"}
            
        # Idempotency Check
        existing_capture = db.query(AuditEvent).filter(
            AuditEvent.razorpay_order_id == order_id,
            AuditEvent.status == AuditStatusEnum.captured
        ).first()
        
        if existing_capture:
            return {"status": "success", "message": "Already processed"}
            
        audit = AuditEvent(
            session_id=session_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            status=AuditStatusEnum.captured,
            detail={"event": "payment.captured", "method": payment.get('method')}
        )
        db.add(audit)
        db.commit()
        return {"status": "success", "message": "Payment captured recorded"}
        
    elif event_type == 'payment.failed':
        payment = payload['payload']['payment']['entity']
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        notes = payment.get('notes', {})
        session_id_str = notes.get('session_id')
        
        if not order_id or not session_id_str:
            return {"status": "ignored", "reason": "Missing order_id or session_id in notes"}
            
        try:
            session_id = uuid.UUID(session_id_str)
        except ValueError:
            return {"status": "ignored", "reason": "Invalid session_id format"}
            
        audit = AuditEvent(
            session_id=session_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            status=AuditStatusEnum.failed,
            detail={
                "event": "payment.failed",
                "error_code": payment.get('error_code'),
                "error_description": payment.get('error_description')
            }
        )
        db.add(audit)
        db.commit()
        return {"status": "success", "message": "Payment failure recorded"}
        
    return {"status": "ignored", "reason": f"Unhandled event type: {event_type}"}
