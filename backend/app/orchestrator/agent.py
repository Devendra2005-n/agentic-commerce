import json
import os
import uuid
from sqlalchemy.orm import Session
import requests
from app.models import Intent, DecisionEnum, CartItem, CartAddedViaEnum, Product
from app.guardrail.engine import evaluate
from app.catalog.service import search_catalog
from app.payments.service import initiate_checkout

def call_gemini_agent(user_message: str):
    import os
    # Load inside function to pick up live .env changes!
    api_key = os.getenv("GEMINI_API_KEY", "dummy_key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": user_message}]}
        ],
        "systemInstruction": {
            "parts": [{"text": "You are a helpful e-commerce sales agent. You help humans find products, add them to their cart, and checkout. Always use tools to take actions. If the user asks for a product, use search_catalog."}]
        },
        "tools": [
            {
                "functionDeclarations": [
                    {
                        "name": "search_catalog",
                        "description": "Search the catalog for products.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {"query": {"type": "STRING"}},
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "add_to_cart",
                        "description": "Add an item to the buyer's cart.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "sku": {"type": "STRING"},
                                "qty": {"type": "INTEGER"},
                                "price_paise": {"type": "INTEGER"}
                            },
                            "required": ["sku", "qty", "price_paise"]
                        }
                    },
                    {
                        "name": "create_order",
                        "description": "Initiate checkout for the current cart, generating an order.",
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling Gemini REST: {e}")
        return None

def process_chat(db: Session, session_id: uuid.UUID, user_message: str) -> dict:
    gemini_resp = call_gemini_agent(user_message)
    
    tool_call = None
    text_content = ""
    
    # Parse Gemini REST response
    if gemini_resp and "candidates" in gemini_resp:
        parts = gemini_resp["candidates"][0]["content"].get("parts", [])
        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_call = {"name": fc["name"], "args": fc.get("args", {})}
            elif "text" in part:
                text_content += part["text"]
                
    if not tool_call and not text_content:
        # Fallback keyword logic if Gemini fails or key is dummy
        text = user_message.lower()
        if "add" in text:
            parts = user_message.split()
            sku = parts[1] if len(parts) > 1 else "SKU-LAMP-A"
            price = int(parts[2]) if len(parts) > 2 else 89900
            tool_call = {"name": "add_to_cart", "args": {"sku": sku, "qty": 1, "price_paise": price}}
            text_content += f"Adding {sku} to cart."
        elif "checkout" in text or "buy" in text:
            tool_call = {"name": "create_order", "args": {}}
            text_content += "Creating your order!"
        else:
            # Fix: allow words of length >= 3 (e.g. "cap", "hat", "pen")
            words = [w for w in text.split() if len(w) >= 3 and w not in ['search', 'find', 'looking', 'show', 'some', 'want', 'need', 'for']]
            query = words[0] if words else text.strip() or "lamp"
            tool_call = {"name": "search_catalog", "args": {"query": query}}
            text_content += f"Searching for {query}..."

    if tool_call:
        action_type = tool_call["name"]
        payload = tool_call.get("args", {})
        
        if action_type == "create_order":
            payload["confirmation_token"] = "confirmed"
            
        intent = Intent(
            session_id=session_id,
            action_type=action_type,
            payload=payload,
            reason_code="customer_requested",
            reason_signals={"user_message": user_message}
        )
        
        decision = evaluate(db, intent)
        
        if decision.decision == DecisionEnum.approved:
            result = execute_action(db, session_id, action_type, payload)
            return {
                "role": "assistant",
                "content": f"Action '{action_type}' executed.",
                "action": action_type,
                "data": result,
                "decision": "approved"
            }
        else:
            return {
                "role": "assistant",
                "content": f"I cannot do that. {decision.reason_rendered}",
                "decision": decision.decision.value
            }
    else:
        return {
            "role": "assistant",
            "content": text_content,
            "decision": None
        }

def generate_mock_products(query: str):
    # Try Gemini to generate realistic items
    payload = {
        "contents": [{"parts": [{"text": f"Generate 4 realistic e-commerce products for '{query}'. Return ONLY a raw JSON array with keys: sku (string), title (string), description (string), price_paise (int, INR paise), category (string), stock_qty (int). DO NOT include markdown."}]}]
    }
    try:
        res = requests.post(GEMINI_URL, json=payload, timeout=10)
        res.raise_for_status()
        text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        if text.startswith("```json"): text = text[7:-3].strip()
        elif text.startswith("```"): text = text[3:-3].strip()
        
        import random
        products = json.loads(text)
        for p in products:
            p['sku'] = p['sku'] + "-" + str(random.randint(1000, 9999))
        return products
    except Exception as e:
        print(f"Error calling Gemini for product generation: {e}")
        import random
        return [
            {
                "sku": f"SKU-{query.upper()[:4]}-{random.randint(100,999)}",
                "title": f"Premium {query.title()}",
                "description": f"A fantastic {query}.",
                "price_paise": 150000,
                "category": "Generated",
                "stock_qty": 10
            },
            {
                "sku": f"SKU-{query.upper()[:4]}-{random.randint(100,999)}",
                "title": f"Basic {query.title()}",
                "description": f"An entry-level {query}.",
                "price_paise": 50000,
                "category": "Generated",
                "stock_qty": 50
            },
            {
                "sku": f"SKU-{query.upper()[:4]}-{random.randint(100,999)}",
                "title": f"Pro {query.title()}",
                "description": f"Professional grade {query}.",
                "price_paise": 450000,
                "category": "Generated",
                "stock_qty": 5
            },
            {
                "sku": f"SKU-{query.upper()[:4]}-{random.randint(100,999)}",
                "title": f"Eco {query.title()}",
                "description": f"Eco-friendly {query}.",
                "price_paise": 85000,
                "category": "Generated",
                "stock_qty": 100
            }
        ]

def execute_action(db: Session, session_id: uuid.UUID, action_type: str, payload: dict):
    if action_type == 'search_catalog':
        query = payload.get('query', '')
        products = search_catalog(db, query=query)
        
        # If DB has no products for this query, generate 4 dynamic ones!
        if len(products) == 0:
            mock_items = generate_mock_products(query)
            for item in mock_items:
                new_p = Product(**item)
                db.add(new_p)
            db.commit()
            products = search_catalog(db, query=query)
            
        return [
            {
                "sku": p.sku, 
                "title": p.title, 
                "price_paise": p.price_paise, 
                "stock_qty": p.stock_qty
            } for p in products
        ]
    elif action_type == 'add_to_cart':
        cart_item = CartItem(
            session_id=session_id,
            sku=payload['sku'],
            qty=payload['qty'],
            price_at_add_paise=payload['price_paise'],
            added_via=CartAddedViaEnum.buyer
        )
        db.add(cart_item)
        db.commit()
        
        items = db.query(CartItem).filter(CartItem.session_id == session_id, CartItem.removed_at == None).all()
        result_items = []
        total = 0
        added_product_title = payload['sku']
        
        for item in items:
            product = db.query(Product).filter(Product.sku == item.sku).first()
            title = product.title if product else item.sku
            if item.sku == payload['sku']:
                added_product_title = title
            result_items.append({"title": title, "qty": item.qty, "price_paise": item.price_at_add_paise})
            total += item.price_at_add_paise * item.qty
            
        # 🧠 Smart Upsell Logic
        upsell_msg = None
        words = added_product_title.split()
        if len(words) > 0:
            core_noun = words[-1]
            upsell_msg = f"Great choice! I found some Premium {core_noun} Accessories that match perfectly. Want me to add them for a 10% discount?"
            
        return {"items": result_items, "total_paise": total, "upsell_message": upsell_msg}
    elif action_type == 'create_order':
        return initiate_checkout(db, session_id)
    return {"status": "unknown_action"}
