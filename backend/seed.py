import random
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Product, MerchantConfig
import uuid

def seed_db():
    print("Connecting to database...")
    db = SessionLocal()
    
    # 1. Create Merchant Config
    existing_config = db.query(MerchantConfig).first()
    if not existing_config:
        print("Seeding Merchant Config...")
        config = MerchantConfig(
            merchant_id="merchant_meera_01",
            display_name="Meera's Home Goods",
            max_order_paise=500000, # 5000 INR
            max_discount_pct=15.00,
            max_upsell_attempts=2,
            upsell_cooldown_sec=120,
            razorpay_key_id="rzp_test_TSfHa8QhpL6X3t",
            razorpay_key_secret_enc=b"6p9mQ071e9K79OwurJLOSiBJ",
            webhook_secret_enc=b"mock_webhook"
        )
        db.add(config)
    else:
        # Update existing config with the real key
        existing_config.razorpay_key_id = "rzp_test_TSfHa8QhpL6X3t"
        existing_config.razorpay_key_secret_enc = b"6p9mQ071e9K79OwurJLOSiBJ"
    
    # 2. Create Products
    print("Seeding 50 Products...")
    categories = ["lighting", "furniture", "accessories", "electronics"]
    images = [
        "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=400&q=80",
        "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=400&q=80",
        "https://images.unsplash.com/photo-1493612276216-ee3925520721?w=400&q=80",
        "https://images.unsplash.com/photo-1505843490538-5133c6c7d0e1?w=400&q=80",
        "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=400&q=80"
    ]
    for i in range(1, 51):
        sku = f"PROD_{i}"
        existing = db.query(Product).filter(Product.sku == sku).first()
        if not existing:
            cat = random.choice(categories)
            prod = Product(
                sku=sku,
                title=f"Premium {cat.title()} Item {i}",
                description=random.choice(images), 
                price_paise=random.randint(50000, 500000),
                stock_qty=random.randint(0, 100),
                category=cat,
                is_promotable=True
            )
            db.add(prod)
            
    db.commit()
    print("Database seeding complete! ✅")
    db.close()

if __name__ == "__main__":
    seed_db()
