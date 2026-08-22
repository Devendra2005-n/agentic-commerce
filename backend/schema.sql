-- 0001_extensions_and_enums
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE actor_type_enum AS ENUM ('human', 'agent');
CREATE TYPE session_status_enum AS ENUM ('active', 'checked_out', 'abandoned');
CREATE TYPE cart_added_via_enum AS ENUM ('buyer', 'upsell_accepted', 'agent');
CREATE TYPE decision_enum AS ENUM ('approved', 'rejected', 'gated_pending');
CREATE TYPE gate_level_enum AS ENUM ('auto', 'soft', 'hard');
CREATE TYPE audit_status_enum AS ENUM (
  'created', 'awaiting_payment', 'captured', 'failed', 'cancelled'
);

-- 0002_products
CREATE TABLE products (
  sku                TEXT PRIMARY KEY,
  title               TEXT NOT NULL,
  description          TEXT,
  price_paise          INTEGER NOT NULL CHECK (price_paise > 0),
  currency             TEXT NOT NULL DEFAULT 'INR' CHECK (currency = 'INR'),
  stock_qty            INTEGER NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
  category             TEXT,
  style_tags           TEXT[] DEFAULT '{}',
  shipping_eta_days    INTEGER CHECK (shipping_eta_days >= 0),
  is_promotable        BOOLEAN NOT NULL DEFAULT false,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_products_style_tags ON products USING GIN (style_tags);
CREATE INDEX idx_products_promotable ON products (is_promotable) WHERE is_promotable = true;

-- 0003_agent_tokens
CREATE TABLE agent_tokens (
  token_id         TEXT PRIMARY KEY,
  agent_name        TEXT NOT NULL,
  on_behalf_of      TEXT NOT NULL,
  max_txn_paise     INTEGER NOT NULL CHECK (max_txn_paise > 0),
  issued_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at        TIMESTAMPTZ NOT NULL,
  consumed_at       TIMESTAMPTZ,
  revoked            BOOLEAN NOT NULL DEFAULT false,
  revoked_reason     TEXT
);
CREATE INDEX idx_agent_tokens_active ON agent_tokens (token_id) WHERE revoked = false AND consumed_at IS NULL;

-- 0004_merchant_config
CREATE TABLE merchant_config (
  merchant_id           TEXT PRIMARY KEY,
  display_name          TEXT NOT NULL,
  max_order_paise       INTEGER NOT NULL CHECK (max_order_paise > 0),
  max_discount_pct      NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (max_discount_pct BETWEEN 0 AND 100),
  max_upsell_attempts   INTEGER NOT NULL DEFAULT 1 CHECK (max_upsell_attempts >= 0),
  upsell_cooldown_sec   INTEGER NOT NULL DEFAULT 60 CHECK (upsell_cooldown_sec >= 0),
  promotable_skus       TEXT[] DEFAULT '{}',
  razorpay_key_id       TEXT NOT NULL,
  razorpay_key_secret_enc BYTEA NOT NULL,
  webhook_secret_enc    BYTEA NOT NULL,
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by            TEXT
);

-- 0005_sessions
CREATE TABLE sessions (
  session_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id      TEXT NOT NULL REFERENCES merchant_config(merchant_id),
  actor_type       actor_type_enum NOT NULL,
  agent_token_id   TEXT REFERENCES agent_tokens(token_id),
  buyer_ref        TEXT,
  status           session_status_enum NOT NULL DEFAULT 'active',
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sessions_merchant_status ON sessions (merchant_id, status);
CREATE INDEX idx_sessions_started_at ON sessions (started_at DESC);

CREATE OR REPLACE FUNCTION check_agent_token_consistency() RETURNS trigger AS $$
BEGIN
  IF NEW.actor_type = 'agent' AND NEW.agent_token_id IS NULL THEN
    RAISE EXCEPTION 'agent sessions must reference an agent_token_id';
  END IF;
  IF NEW.actor_type = 'human' AND NEW.agent_token_id IS NOT NULL THEN
    RAISE EXCEPTION 'human sessions must not reference an agent_token_id';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_agent_token_consistency
BEFORE INSERT OR UPDATE ON sessions
FOR EACH ROW EXECUTE FUNCTION check_agent_token_consistency();

-- 0006_cart_items
CREATE TABLE cart_items (
  id                    BIGSERIAL PRIMARY KEY,
  session_id            UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  sku                    TEXT NOT NULL REFERENCES products(sku),
  qty                    INTEGER NOT NULL CHECK (qty > 0),
  price_at_add_paise     INTEGER NOT NULL CHECK (price_at_add_paise > 0),
  added_via              cart_added_via_enum NOT NULL,
  added_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  removed_at             TIMESTAMPTZ
);
CREATE INDEX idx_cart_items_session ON cart_items (session_id) WHERE removed_at IS NULL;

-- 0007_intents
CREATE TABLE intents (
  intent_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id        UUID NOT NULL REFERENCES sessions(session_id),
  action_type       TEXT NOT NULL,
  payload            JSONB NOT NULL,
  reason_code        TEXT,
  reason_signals     JSONB,
  submitted_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_intents_session ON intents (session_id, submitted_at);
CREATE INDEX idx_intents_action_type ON intents (action_type);

-- 0008_decisions
CREATE TABLE decisions (
  decision_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id        UUID NOT NULL UNIQUE REFERENCES intents(intent_id),
  decision          decision_enum NOT NULL,
  gate_level        gate_level_enum NOT NULL,
  checks_run        JSONB NOT NULL,
  reason_rendered   TEXT NOT NULL,
  decided_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_decisions_intent ON decisions (intent_id);
CREATE INDEX idx_decisions_decision ON decisions (decision);

-- 0009_audit_events
CREATE TABLE audit_events (
  event_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id             UUID NOT NULL REFERENCES sessions(session_id),
  intent_id              UUID REFERENCES intents(intent_id),
  decision_id             UUID REFERENCES decisions(decision_id),
  razorpay_order_id       TEXT,
  razorpay_payment_id     TEXT,
  status                   audit_status_enum NOT NULL,
  detail                   JSONB,
  event_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_events_session ON audit_events (session_id, event_at);
CREATE INDEX idx_audit_events_order ON audit_events (razorpay_order_id);
CREATE INDEX idx_audit_events_payment ON audit_events (razorpay_payment_id);
CREATE INDEX idx_audit_events_status ON audit_events (status);
CREATE UNIQUE INDEX uq_audit_events_captured_once ON audit_events (razorpay_payment_id) WHERE status = 'captured';

-- 0010_append_only_triggers
CREATE OR REPLACE FUNCTION reject_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '% is append-only; % is not permitted', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_intents_append_only BEFORE UPDATE OR DELETE ON intents FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER trg_decisions_append_only BEFORE UPDATE OR DELETE ON decisions FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER trg_audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_mutation();

-- 0011_views
CREATE VIEW v_session_timeline AS
SELECT
  s.session_id,
  s.actor_type,
  i.intent_id,
  i.action_type,
  i.submitted_at,
  d.decision,
  d.gate_level,
  d.checks_run,
  d.reason_rendered,
  ae.status AS audit_status,
  ae.razorpay_order_id,
  ae.razorpay_payment_id,
  ae.event_at
FROM sessions s
LEFT JOIN intents i ON i.session_id = s.session_id
LEFT JOIN decisions d ON d.intent_id = i.intent_id
LEFT JOIN audit_events ae ON ae.intent_id = i.intent_id
ORDER BY s.session_id, COALESCE(i.submitted_at, ae.event_at);

CREATE VIEW v_merchant_config_safe AS
SELECT
  merchant_id, display_name, max_order_paise, max_discount_pct,
  max_upsell_attempts, upsell_cooldown_sec, promotable_skus, updated_at, updated_by
FROM merchant_config;
