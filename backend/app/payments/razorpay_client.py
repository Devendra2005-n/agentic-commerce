import razorpay
from cryptography.fernet import Fernet
import os

def get_decrypted_secret(encrypted_bytes: bytes) -> str:
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY env var not set")
    f = Fernet(encryption_key.encode())
    return f.decrypt(encrypted_bytes).decode('utf-8')

def get_razorpay_client(key_id: str, key_secret_enc: bytes) -> razorpay.Client:
    key_secret = get_decrypted_secret(key_secret_enc)
    client = razorpay.Client(auth=(key_id, key_secret))
    client.cert_path = False # Razorpay SDK explicitly passes this in the request, overriding session
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return client

def create_rzp_order(client: razorpay.Client, amount_paise: int, receipt_id: str, notes: dict = None) -> dict:
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "notes": notes or {}
    }
    return client.order.create(data=data)

def create_rzp_payment_link(client: razorpay.Client, amount_paise: int, reference_id: str, description: str, notes: dict = None) -> dict:
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": reference_id,
        "description": description,
        "notes": notes or {}
    }
    return client.payment_link.create(data)

def verify_webhook_signature(client: razorpay.Client, body: str, signature: str, secret: str) -> bool:
    try:
        # The razorpay SDK has a utility function for this
        client.utility.verify_webhook_signature(body, signature, secret)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
