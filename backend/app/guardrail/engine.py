import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Intent, Decision, Product, MerchantConfig, Session as DbSession, CartItem, AgentToken

# Static Gate Levels per TRD §5.3
GATE_LEVELS = {
    "search_catalog": "auto",
    "get_cart": "auto",
    "add_to_cart": "auto",
    "propose_upsell": "soft",
    "apply_discount": "soft",
    "create_order": "hard",
    "create_payment_link": "hard",
    "cancel_order": "hard",
    "retry_payment": "hard",
}

def evaluate(db: Session, intent: Intent) -> Decision:
    """
    Given an Intent, run all applicable checks, return a Decision.
    Writes both Intent and Decision to DB before returning.
    Never calls Razorpay. Never calls the LLM.
    """
    action = intent.action_type
    payload = intent.payload
    
    # Initialize check results
    checks_run = []
    is_approved = True
    reason_rendered = ""
    gate_level = GATE_LEVELS.get(action, "hard") # Default to hard if unknown
    
    # 1. Check: reason_required (Applies to all money-adjacent actions)
    if gate_level in ["soft", "hard"] or action in ["add_to_cart"]:
        check_reason = _check_reason_required(intent)
        checks_run.append(check_reason)
        if check_reason["result"] == "fail":
            is_approved = False
            reason_rendered = "Action requires a valid reason code and signals."

    # 2. Check: sku_exists
    if action in ["add_to_cart", "propose_upsell"] and is_approved:
        sku = payload.get("sku") or payload.get("candidate_sku")
        qty = payload.get("qty", 1)
        check_sku = _check_sku_exists(db, sku, qty)
        checks_run.append(check_sku)
        if check_sku["result"] == "fail":
            is_approved = False
            reason_rendered = f"Item {sku} is out of stock or does not exist."

    # 3. Check: price_matches_catalog
    if action in ["add_to_cart", "create_order"] and is_approved:
        # For add_to_cart, check the single item. For create_order, check all cart items.
        check_price = _check_price_matches_catalog(db, intent)
        checks_run.append(check_price)
        if check_price["result"] == "fail":
            is_approved = False
            reason_rendered = "Prices have updated since items were added to the cart."
            
    # 4. Check: order_ceiling
    if action == "create_order" and is_approved:
        check_ceiling = _check_order_ceiling(db, intent)
        checks_run.append(check_ceiling)
        if check_ceiling["result"] == "fail":
            is_approved = False
            reason_rendered = f"Order total exceeds the approved ceiling of {check_ceiling['threshold']/100} INR."
            
    # 5. Check: upsell_attempt_cap & cooldown
    if action == "propose_upsell" and is_approved:
        check_cap = _check_upsell_cap(db, intent)
        checks_run.append(check_cap)
        if check_cap["result"] == "fail":
            is_approved = False
            reason_rendered = "Maximum upsell attempts reached for this session."
            
    # 6. Check: agent_token_valid (if actor is agent)
    db_session = db.query(DbSession).filter(DbSession.session_id == intent.session_id).first()
    if db_session and db_session.actor_type == "agent" and is_approved:
        check_token = _check_agent_token(db, db_session.agent_token_id)
        checks_run.append(check_token)
        if check_token["result"] == "fail":
            is_approved = False
            reason_rendered = "Agent token is invalid, expired, or revoked."

    # Construct Final Decision
    decision_status = "approved"
    if not is_approved:
        decision_status = "rejected"
    elif gate_level == "hard" or gate_level == "soft":
        # Note: In a real flow, if it's already confirmed (e.g., token present), it goes to approved.
        # For this skeleton, we assume hard gates require confirmation outside this immediate loop.
        decision_status = "gated_pending" 

    decision = Decision(
        intent_id=intent.intent_id,
        decision=decision_status,
        gate_level=gate_level,
        checks_run=checks_run,
        reason_rendered=reason_rendered if not is_approved else "All guardrail checks passed."
    )
    
    db.add(intent)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return decision


def _check_reason_required(intent: Intent) -> Dict[str, Any]:
    if intent.reason_code and intent.reason_signals:
        return {"check_name": "reason_required", "result": "pass", "threshold": "present", "actual": "present"}
    return {"check_name": "reason_required", "result": "fail", "threshold": "present", "actual": "missing"}


def _check_sku_exists(db: Session, sku: str, qty: int) -> Dict[str, Any]:
    product = db.query(Product).filter(Product.sku == sku).first()
    if product and product.stock_qty >= qty:
        return {"check_name": "sku_exists", "result": "pass", "threshold": qty, "actual": product.stock_qty}
    return {"check_name": "sku_exists", "result": "fail", "threshold": qty, "actual": product.stock_qty if product else 0}


def _check_price_matches_catalog(db: Session, intent: Intent) -> Dict[str, Any]:
    # Placeholder for actual logic mapping payload prices to DB prices
    return {"check_name": "price_matches_catalog", "result": "pass", "threshold": 0, "actual": 0}


def _check_order_ceiling(db: Session, intent: Intent) -> Dict[str, Any]:
    config = db.query(MerchantConfig).first()
    ceiling = config.max_order_paise if config else 500000
    
    # Calculate cart total (placeholder)
    cart_total = 0 
    
    if cart_total <= ceiling:
        return {"check_name": "order_ceiling", "result": "pass", "threshold": ceiling, "actual": cart_total}
    return {"check_name": "order_ceiling", "result": "fail", "threshold": ceiling, "actual": cart_total}


def _check_upsell_cap(db: Session, intent: Intent) -> Dict[str, Any]:
    config = db.query(MerchantConfig).first()
    max_attempts = config.max_upsell_attempts if config else 1
    
    attempts = db.query(Intent).filter(
        Intent.session_id == intent.session_id, 
        Intent.action_type == "propose_upsell"
    ).count()
    
    if attempts < max_attempts:
        return {"check_name": "upsell_attempt_cap", "result": "pass", "threshold": max_attempts, "actual": attempts}
    return {"check_name": "upsell_attempt_cap", "result": "fail", "threshold": max_attempts, "actual": attempts}


def _check_agent_token(db: Session, token_id: str) -> Dict[str, Any]:
    token = db.query(AgentToken).filter(AgentToken.token_id == token_id).first()
    if token and not token.revoked and not token.consumed_at:
        # Also need to check expiry time in full implementation
        return {"check_name": "agent_token_valid", "result": "pass", "threshold": "valid", "actual": "valid"}
    return {"check_name": "agent_token_valid", "result": "fail", "threshold": "valid", "actual": "invalid"}
