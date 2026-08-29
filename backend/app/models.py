import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, ForeignKey, DateTime, 
    Text, CheckConstraint, Enum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, BYTEA
from sqlalchemy.orm import relationship
import enum
from .database import Base

class ActorTypeEnum(str, enum.Enum):
    human = 'human'
    agent = 'agent'

class SessionStatusEnum(str, enum.Enum):
    active = 'active'
    checked_out = 'checked_out'
    abandoned = 'abandoned'

class CartAddedViaEnum(str, enum.Enum):
    buyer = 'buyer'
    upsell_accepted = 'upsell_accepted'
    agent = 'agent'

class DecisionEnum(str, enum.Enum):
    approved = 'approved'
    rejected = 'rejected'
    gated_pending = 'gated_pending'

class GateLevelEnum(str, enum.Enum):
    auto = 'auto'
    soft = 'soft'
    hard = 'hard'

class AuditStatusEnum(str, enum.Enum):
    created = 'created'
    awaiting_payment = 'awaiting_payment'
    captured = 'captured'
    failed = 'failed'
    cancelled = 'cancelled'

class Product(Base):
    __tablename__ = 'products'
    sku = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    price_paise = Column(Integer, nullable=False)
    currency = Column(Text, nullable=False, default='INR')
    stock_qty = Column(Integer, nullable=False, default=0)
    category = Column(Text)
    style_tags = Column(ARRAY(Text), default=[])
    shipping_eta_days = Column(Integer)
    is_promotable = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('price_paise > 0', name='check_price_positive'),
        CheckConstraint("currency = 'INR'", name='check_currency_inr'),
        CheckConstraint('stock_qty >= 0', name='check_stock_non_negative'),
        CheckConstraint('shipping_eta_days >= 0', name='check_shipping_non_negative'),
    )

class MerchantConfig(Base):
    __tablename__ = 'merchant_config'
    merchant_id = Column(Text, primary_key=True)
    display_name = Column(Text, nullable=False)
    max_order_paise = Column(Integer, nullable=False)
    max_discount_pct = Column(Numeric(5, 2), nullable=False, default=0)
    max_upsell_attempts = Column(Integer, nullable=False, default=1)
    upsell_cooldown_sec = Column(Integer, nullable=False, default=60)
    promotable_skus = Column(ARRAY(Text), default=[])
    razorpay_key_id = Column(Text, nullable=False)
    razorpay_key_secret_enc = Column(BYTEA, nullable=False)
    webhook_secret_enc = Column(BYTEA, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Text)

    __table_args__ = (
        CheckConstraint('max_order_paise > 0', name='check_max_order_positive'),
        CheckConstraint('max_discount_pct BETWEEN 0 AND 100', name='check_discount_range'),
        CheckConstraint('max_upsell_attempts >= 0', name='check_upsell_attempts_positive'),
        CheckConstraint('upsell_cooldown_sec >= 0', name='check_upsell_cooldown_positive'),
    )

class AgentToken(Base):
    __tablename__ = 'agent_tokens'
    token_id = Column(Text, primary_key=True)
    agent_name = Column(Text, nullable=False)
    on_behalf_of = Column(Text, nullable=False)
    max_txn_paise = Column(Integer, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True))
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_reason = Column(Text)

    __table_args__ = (
        CheckConstraint('max_txn_paise > 0', name='check_agent_txn_limit_positive'),
    )

class Session(Base):
    __tablename__ = 'sessions'
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Text, ForeignKey('merchant_config.merchant_id'), nullable=False)
    actor_type = Column(Enum(ActorTypeEnum, name='actor_type_enum'), nullable=False)
    agent_token_id = Column(Text, ForeignKey('agent_tokens.token_id'))
    buyer_ref = Column(Text)
    status = Column(Enum(SessionStatusEnum, name='session_status_enum'), nullable=False, default=SessionStatusEnum.active)
    agent_mode = Column(Text, nullable=False, default="sales")
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_active_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    cart_items = relationship("CartItem", back_populates="session", cascade="all, delete-orphan")
    intents = relationship("Intent", back_populates="session")
    audit_events = relationship("AuditEvent", back_populates="session")

class CartItem(Base):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    sku = Column(Text, ForeignKey('products.sku'), nullable=False)
    qty = Column(Integer, nullable=False)
    price_at_add_paise = Column(Integer, nullable=False)
    added_via = Column(Enum(CartAddedViaEnum, name='cart_added_via_enum'), nullable=False)
    added_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    removed_at = Column(DateTime(timezone=True))
    
    session = relationship("Session", back_populates="cart_items")
    
    __table_args__ = (
        CheckConstraint('qty > 0', name='check_cart_qty_positive'),
        CheckConstraint('price_at_add_paise > 0', name='check_cart_price_positive'),
    )

class Intent(Base):
    __tablename__ = 'intents'
    intent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.session_id', ondelete='RESTRICT'), nullable=False)
    action_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    reason_code = Column(Text)
    reason_signals = Column(JSONB)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="intents")
    decision = relationship("Decision", uselist=False, back_populates="intent")

class Decision(Base):
    __tablename__ = 'decisions'
    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey('intents.intent_id', ondelete='RESTRICT'), nullable=False, unique=True)
    decision = Column(Enum(DecisionEnum, name='decision_enum'), nullable=False)
    gate_level = Column(Enum(GateLevelEnum, name='gate_level_enum'), nullable=False)
    checks_run = Column(JSONB, nullable=False)
    reason_rendered = Column(Text, nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    intent = relationship("Intent", back_populates="decision")

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.session_id', ondelete='RESTRICT'), nullable=False)
    intent_id = Column(UUID(as_uuid=True), ForeignKey('intents.intent_id', ondelete='RESTRICT'))
    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.decision_id', ondelete='RESTRICT'))
    razorpay_order_id = Column(Text)
    razorpay_payment_id = Column(Text)
    status = Column(Enum(AuditStatusEnum, name='audit_status_enum'), nullable=False)
    detail = Column(JSONB)
    event_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="audit_events")
