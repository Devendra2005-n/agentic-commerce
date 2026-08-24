import os
import sys
import uuid
import requests
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models import Session as DbSession, CartItem, Product, ActorTypeEnum, CartAddedViaEnum

def run_test():
    db = SessionLocal()
    
    # 1. Create a session
    session = DbSession(
        merchant_id='demo_merchant_1',
        actor_type=ActorTypeEnum.human
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    print(f"Created Session: {session.session_id}")
    
    # 2. Add an item to the cart
    product = db.query(Product).filter(Product.sku == 'SKU-LAMP-A').first()
    cart_item = CartItem(
        session_id=session.session_id,
        sku=product.sku,
        qty=1,
        price_at_add_paise=product.price_paise,
        added_via=CartAddedViaEnum.buyer
    )
    db.add(cart_item)
    db.commit()
    print(f"Added '{product.title}' to cart for ₹{product.price_paise / 100}")
    
    # 3. Assuming FastAPI is running on port 8000
    print("\nInitiating Checkout via API...")
    try:
        response = requests.post(f"http://localhost:8000/v1/checkout/{session.session_id}")
        response.raise_for_status()
        
        data = response.json()
        print("\n✅ Success! Razorpay Link Created.")
        print(f"Order ID: {data['order_id']}")
        print(f"Payment Link: {data['payment_link_url']}")
        print("\n👉 Click the link above to test the payment UI!")
    except Exception as e:
        print(f"❌ Failed to initiate checkout: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)

if __name__ == "__main__":
    run_test()
