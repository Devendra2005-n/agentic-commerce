import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, ENUM, BYTEA
from .database import Base

class Product(Base):
    __tablename__ = "products"

    sku = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    price_paise = Column(Integer, nullable=False)
    currency = Column(Text, nullable=False, default="INR")
    stock_qty = Column(Integer, nullable=False, default=0)
    category = Column(Text)
    style_tags = Column(ARRAY(Text), default=[])
    shipping_eta_days = Column(Integer)
    is_promotable = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MerchantConfig(Base):
    __tablename__ = "merchant_config"

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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(Text)


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Text, ForeignKey("merchant_config.merchant_id"), nullable=False)
    actor_type = Column(ENUM('human', 'agent', name='actor_type_enum', create_type=False), nullable=False)
    agent_token_id = Column(Text, ForeignKey("agent_tokens.token_id"), nullable=True)
    buyer_ref = Column(Text)
    status = Column(ENUM('active', 'checked_out', 'abandoned', name='session_status_enum', create_type=False), nullable=False, default='active')
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    chat_history = Column(JSONB, nullable=False, default=[])

    cart_items = relationship("CartItem", back_populates="session")
    intents = relationship("Intent", back_populates="session")
    audit_events = relationship("AuditEvent", back_populates="session")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    sku = Column(Text, ForeignKey("products.sku"), nullable=False)
    qty = Column(Integer, nullable=False)
    price_at_add_paise = Column(Integer, nullable=False)
    added_via = Column(ENUM('buyer', 'upsell_accepted', 'agent', name='cart_added_via_enum', create_type=False), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    removed_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", back_populates="cart_items")
    product = relationship("Product")


class Intent(Base):
    __tablename__ = "intents"

    intent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="RESTRICT"), nullable=False)
    action_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    reason_code = Column(Text)
    reason_signals = Column(JSONB)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="intents")
    decision = relationship("Decision", uselist=False, back_populates="intent")


class Decision(Base):
    __tablename__ = "decisions"

    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("intents.intent_id", ondelete="RESTRICT"), nullable=False, unique=True)
    decision = Column(ENUM('approved', 'rejected', 'gated_pending', name='decision_enum', create_type=False), nullable=False)
    gate_level = Column(ENUM('auto', 'soft', 'hard', name='gate_level_enum', create_type=False), nullable=False)
    checks_run = Column(JSONB, nullable=False)
    reason_rendered = Column(Text, nullable=False)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intent = relationship("Intent", back_populates="decision")


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    token_id = Column(Text, primary_key=True)
    agent_name = Column(Text, nullable=False)
    on_behalf_of = Column(Text, nullable=False)
    max_txn_paise = Column(Integer, nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_reason = Column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("intents.intent_id", ondelete="RESTRICT"), nullable=True)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.decision_id", ondelete="RESTRICT"), nullable=True)
    razorpay_order_id = Column(Text, nullable=True)
    razorpay_payment_id = Column(Text, nullable=True)
    status = Column(ENUM('created', 'awaiting_payment', 'captured', 'failed', 'cancelled', name='audit_status_enum', create_type=False), nullable=False)
    detail = Column(JSONB, nullable=True)
    event_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="audit_events")
