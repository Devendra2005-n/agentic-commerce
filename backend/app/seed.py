import os
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from app.database import SessionLocal, engine
from app.models import Base, Product, MerchantConfig, AgentToken

def seed_db():
    db = SessionLocal()
    try:
        # Seed MerchantConfig
        if not db.query(MerchantConfig).first():
            encryption_key = os.getenv("ENCRYPTION_KEY")
            if not encryption_key:
                encryption_key = Fernet.generate_key().decode()
                print(f"Generated encryption key for dev: {encryption_key}")
            
            f = Fernet(encryption_key.encode())
            merchant = MerchantConfig(
                merchant_id='demo_merchant_1',
                display_name='Meera Home Goods',
                max_order_paise=500000, # ₹5000
                max_discount_pct=10.0,
                max_upsell_attempts=1,
                upsell_cooldown_sec=60,
                promotable_skus=['SKU-LAMP-B', 'SKU-BULB-PACK'],
                razorpay_key_id=os.getenv('RAZORPAY_TEST_KEY_ID', 'test_key'),
                razorpay_key_secret_enc=f.encrypt(os.getenv('RAZORPAY_TEST_KEY_SECRET', 'test_secret').encode()),
                webhook_secret_enc=f.encrypt(os.getenv('RAZORPAY_WEBHOOK_SECRET', 'test_webhook_secret').encode())
            )
            db.add(merchant)
        
        # Seed Products
        products = [
            Product(sku='SKU-LAMP-A', title='Lamp A', description='A basic desk lamp.', price_paise=89900, stock_qty=10, category='Lighting', style_tags=['minimal', 'affordable']),
            Product(sku='SKU-LAMP-B', title='Lamp B', description='A minimal, modern desk lamp.', price_paise=115000, stock_qty=2, category='Lighting', style_tags=['minimal', 'premium'], is_promotable=True),
            Product(sku='SKU-BULB-PACK', title='Warm-white bulb pack', description='Pack of 2 warm-white bulbs.', price_paise=24900, stock_qty=40, category='Lighting', style_tags=['warm', 'accessory'], is_promotable=True),
            Product(sku='SKU-DIFFUSER', title='Aroma Diffuser', description='Minimalist ceramic aroma diffuser.', price_paise=149900, stock_qty=15, category='Home Decor', style_tags=['minimal', 'ceramic']),
            Product(sku='SKU-CANDLE', title='Scented Candle', description='Lavender and vanilla.', price_paise=39900, stock_qty=0, category='Home Decor', style_tags=['scent', 'affordable']),
        ]
        
        for p in products:
            if not db.query(Product).filter(Product.sku == p.sku).first():
                db.add(p)
                
        # Seed Agent Tokens
        now = datetime.utcnow()
        tokens = [
            AgentToken(token_id='tok_valid', agent_name='demo-shopping-agent', on_behalf_of='user_123', max_txn_paise=150000, expires_at=now + timedelta(hours=1)),
            AgentToken(token_id='tok_expired', agent_name='demo-shopping-agent', on_behalf_of='user_456', max_txn_paise=150000, expires_at=now - timedelta(hours=1)),
            AgentToken(token_id='tok_revoked', agent_name='demo-shopping-agent', on_behalf_of='user_789', max_txn_paise=150000, expires_at=now + timedelta(hours=1), revoked=True, revoked_reason='Manually revoked'),
        ]
        
        for t in tokens:
            if not db.query(AgentToken).filter(AgentToken.token_id == t.token_id).first():
                db.add(t)
                
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
