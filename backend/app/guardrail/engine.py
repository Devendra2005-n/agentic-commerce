from sqlalchemy.orm import Session
from app.models import Intent, Decision, MerchantConfig, AgentToken, Session as DbSession, CartItem, DecisionEnum, GateLevelEnum
from app.guardrail.checks import CHECK_REGISTRY, ACTION_CHECKS

GATE_LEVELS = {
    'search_catalog': GateLevelEnum.auto,
    'get_cart': GateLevelEnum.auto,
    'add_to_cart': GateLevelEnum.auto,
    'propose_upsell': GateLevelEnum.soft,
    'apply_discount': GateLevelEnum.soft,
    'create_order': GateLevelEnum.hard,
    'create_payment_link': GateLevelEnum.hard,
    'cancel_order': GateLevelEnum.hard,
    'retry_payment': GateLevelEnum.hard,
}

def evaluate(db: Session, intent: Intent) -> Decision:
    session_db = db.query(DbSession).filter(DbSession.session_id == intent.session_id).first()
    merchant_config = db.query(MerchantConfig).filter(MerchantConfig.merchant_id == session_db.merchant_id).first()
    
    agent_token = None
    if session_db.actor_type.value == 'agent' and session_db.agent_token_id:
        agent_token = db.query(AgentToken).filter(AgentToken.token_id == session_db.agent_token_id).first()
        
    cart_items = db.query(CartItem).filter(CartItem.session_id == intent.session_id, CartItem.removed_at == None).all()
    cart_total_paise = sum(item.price_at_add_paise * item.qty for item in cart_items)
    
    context = {
        'merchant_config': merchant_config,
        'session': session_db,
        'agent_token': agent_token,
        'cart_items': cart_items,
        'cart_total_paise': cart_total_paise
    }
    
    check_names = ACTION_CHECKS.get(intent.action_type, [])
    checks_run = []
    decision_status = DecisionEnum.approved
    gate_level = GATE_LEVELS.get(intent.action_type, GateLevelEnum.hard)
    
    rejected_reason = None
    
    for check_name in check_names:
        check_fn = CHECK_REGISTRY[check_name]
        try:
            result = check_fn(db, intent, context)
            checks_run.append(result.to_dict())
            if result.result == 'fail':
                decision_status = DecisionEnum.rejected
                rejected_reason = f"{check_name} failed. Actual: {result.actual} vs Threshold: {result.threshold}"
                break
        except Exception as e:
            decision_status = DecisionEnum.rejected
            checks_run.append({"check_name": check_name, "result": "error", "actual": str(e)})
            rejected_reason = "Internal guardrail error."
            break
            
    if decision_status == DecisionEnum.rejected:
        reason_rendered = rejected_reason or "Request rejected by guardrails."
    elif gate_level != GateLevelEnum.auto:
        # Check for confirmation in payload
        if intent.payload.get('confirmation_token'):
            decision_status = DecisionEnum.approved
            reason_rendered = "Action approved and confirmed."
        else:
            decision_status = DecisionEnum.gated_pending
            reason_rendered = "Action pending confirmation."
    else:
        reason_rendered = "Action approved automatically."
        
    db.add(intent)
    db.flush()
    
    decision = Decision(
        intent_id=intent.intent_id,
        decision=decision_status,
        gate_level=gate_level,
        checks_run=checks_run,
        reason_rendered=reason_rendered
    )
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return decision
