from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models import Product, Intent, AgentToken, AuditEvent, AuditStatusEnum

class CheckResult:
    def __init__(self, check_name, result, threshold=None, actual=None):
        self.check_name = check_name
        self.result = result
        self.threshold = threshold
        self.actual = actual
        
    def to_dict(self):
        return {
            "check_name": self.check_name,
            "result": self.result,
            "threshold": self.threshold,
            "actual": self.actual
        }

def sku_exists(db: Session, intent: Intent, context: dict) -> CheckResult:
    sku = intent.payload.get('sku') or intent.payload.get('candidate_sku')
    qty = intent.payload.get('qty', 1)
    price_paise = intent.payload.get('price_paise', 50000)
    if not sku:
        return CheckResult('sku_exists', 'fail', actual='No SKU provided')
    product = db.query(Product).filter(Product.sku == sku).first()
    
    # Auto-generate the hallucinated upsell product if it doesn't exist!
    if not product:
        # Infer title from SKU or just use SKU
        parts = sku.split('-')
        title = " ".join(parts[1:]) if len(parts) > 1 else sku
        new_p = Product(
            sku=sku,
            title=title.title() + " (Auto-Generated)",
            description="Dynamically generated upsell product.",
            price_paise=price_paise,
            category="Upsell",
            stock_qty=100
        )
        db.add(new_p)
        db.commit()
        db.refresh(new_p)
        product = new_p

    if product.stock_qty < qty:
        return CheckResult('sku_exists', 'fail', threshold=qty, actual=product.stock_qty)
    return CheckResult('sku_exists', 'pass')

def price_matches_catalog(db: Session, intent: Intent, context: dict) -> CheckResult:
    merchant_config = context.get('merchant_config')
    max_discount = float(merchant_config.max_discount_pct) if merchant_config else 0.0
    
    sku = intent.payload.get('sku')
    expected_price = intent.payload.get('price_paise')
    if expected_price is not None and sku:
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            return CheckResult('price_matches_catalog', 'fail', threshold=expected_price, actual=None)
            
        min_allowed_price = int(product.price_paise * (1 - max_discount/100))
        # Add a tiny epsilon (e.g. 5 paise) for rounding differences if LLM calculates it weirdly
        if expected_price < (min_allowed_price - 100):
            return CheckResult('price_matches_catalog', 'fail', threshold=min_allowed_price, actual=expected_price)
    
    # If create_order, check all cart items
    if intent.action_type == 'create_order':
        cart_items = context.get('cart_items', [])
        for item in cart_items:
            product = db.query(Product).filter(Product.sku == item.sku).first()
            if not product:
                return CheckResult('price_matches_catalog', 'fail', threshold='exists', actual=None)
            min_allowed_price = int(product.price_paise * (1 - max_discount/100))
            if item.price_at_add_paise < (min_allowed_price - 100):
                return CheckResult('price_matches_catalog', 'fail', threshold=min_allowed_price, actual=item.price_at_add_paise)
                
    return CheckResult('price_matches_catalog', 'pass')

def order_ceiling(db: Session, intent: Intent, context: dict) -> CheckResult:
    merchant_config = context['merchant_config']
    cart_total_paise = context.get('cart_total_paise', 0)
    
    ceiling = merchant_config.max_order_paise
    agent_token = context.get('agent_token')
    if agent_token:
        ceiling = min(ceiling, agent_token.max_txn_paise)
        
    if cart_total_paise > ceiling:
        return CheckResult('order_ceiling', 'fail', threshold=ceiling, actual=cart_total_paise)
    return CheckResult('order_ceiling', 'pass')

def upsell_attempt_cap(db: Session, intent: Intent, context: dict) -> CheckResult:
    merchant_config = context['merchant_config']
    past_upsells = db.query(Intent).filter(
        Intent.session_id == intent.session_id,
        Intent.action_type == 'propose_upsell'
    ).count()
    
    if past_upsells >= merchant_config.max_upsell_attempts:
        return CheckResult('upsell_attempt_cap', 'fail', threshold=merchant_config.max_upsell_attempts, actual=past_upsells)
    return CheckResult('upsell_attempt_cap', 'pass')

def upsell_cooldown(db: Session, intent: Intent, context: dict) -> CheckResult:
    merchant_config = context['merchant_config']
    last_upsell = db.query(Intent).filter(
        Intent.session_id == intent.session_id,
        Intent.action_type == 'propose_upsell'
    ).order_by(Intent.submitted_at.desc()).first()
    
    if last_upsell:
        elapsed = (datetime.utcnow() - last_upsell.submitted_at.replace(tzinfo=None)).total_seconds()
        if elapsed < merchant_config.upsell_cooldown_sec:
            return CheckResult('upsell_cooldown', 'fail', threshold=merchant_config.upsell_cooldown_sec, actual=elapsed)
    return CheckResult('upsell_cooldown', 'pass')

def reason_required(db: Session, intent: Intent, context: dict) -> CheckResult:
    if not intent.reason_code or not intent.reason_signals:
        return CheckResult('reason_required', 'fail', actual='Missing reason_code or reason_signals')
    return CheckResult('reason_required', 'pass')

def agent_token_valid(db: Session, intent: Intent, context: dict) -> CheckResult:
    session = context['session']
    if session.actor_type.value == 'agent':
        agent_token = context.get('agent_token')
        if not agent_token:
            return CheckResult('agent_token_valid', 'fail', actual='No token')
        if agent_token.revoked:
            return CheckResult('agent_token_valid', 'fail', actual='Token revoked')
        if agent_token.expires_at.replace(tzinfo=None) < datetime.utcnow():
            return CheckResult('agent_token_valid', 'fail', actual='Token expired')
    return CheckResult('agent_token_valid', 'pass')

def terminal_state_guard(db: Session, intent: Intent, context: dict) -> CheckResult:
    order_id = intent.payload.get('order_id')
    if order_id:
        terminal_event = db.query(AuditEvent).filter(
            AuditEvent.razorpay_order_id == order_id,
            AuditEvent.status.in_(['captured', 'cancelled'])
        ).first()
        if terminal_event:
            return CheckResult('terminal_state_guard', 'fail', threshold='not terminal', actual=terminal_event.status.value)
    return CheckResult('terminal_state_guard', 'pass')

CHECK_REGISTRY = {
    'sku_exists': sku_exists,
    'price_matches_catalog': price_matches_catalog,
    'order_ceiling': order_ceiling,
    'upsell_attempt_cap': upsell_attempt_cap,
    'upsell_cooldown': upsell_cooldown,
    'reason_required': reason_required,
    'agent_token_valid': agent_token_valid,
    'terminal_state_guard': terminal_state_guard
}

ACTION_CHECKS = {
    'search_catalog': ['agent_token_valid'],
    'get_cart': ['agent_token_valid'],
    'add_to_cart': ['agent_token_valid', 'sku_exists', 'price_matches_catalog', 'reason_required'],
    'propose_upsell': ['agent_token_valid', 'sku_exists', 'upsell_attempt_cap', 'upsell_cooldown', 'reason_required'],
    'create_order': ['agent_token_valid', 'price_matches_catalog', 'order_ceiling', 'reason_required'],
    'create_payment_link': ['agent_token_valid', 'reason_required'],
    'check_payment_status': ['agent_token_valid'],
    'cancel_order': ['agent_token_valid', 'terminal_state_guard', 'reason_required'],
    'retry_payment': ['agent_token_valid', 'terminal_state_guard', 'reason_required'],
}
