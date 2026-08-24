import os
import sys
from dotenv import load_dotenv
from cryptography.fernet import Fernet

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models import MerchantConfig

def main():
    db = SessionLocal()
    key_id = os.getenv('RAZORPAY_TEST_KEY_ID')
    key_secret = os.getenv('RAZORPAY_TEST_KEY_SECRET')
    webhook_secret = os.getenv('RAZORPAY_WEBHOOK_SECRET')
    enc_key = os.getenv('ENCRYPTION_KEY')
    
    if not all([key_id, key_secret, webhook_secret, enc_key]):
        print("Error: Missing one of the required environment variables in .env")
        return
        
    f = Fernet(enc_key.encode())
    
    merchant = db.query(MerchantConfig).first()
    if not merchant:
        print("Error: No merchant found in database.")
        return
        
    merchant.razorpay_key_id = key_id
    merchant.razorpay_key_secret_enc = f.encrypt(key_secret.encode())
    merchant.webhook_secret_enc = f.encrypt(webhook_secret.encode())
    
    db.commit()
    print(f"Successfully updated DB for merchant '{merchant.merchant_id}' with keys from .env")

if __name__ == "__main__":
    main()
