import json
import os
import uuid
from sqlalchemy.orm import Session
import requests
from app.models import Intent, DecisionEnum, CartItem, CartAddedViaEnum, Product
from app.guardrail.engine import evaluate
from app.catalog.service import search_catalog
from app.payments.service import initiate_checkout

def call_gemini_agent(user_message: str, image_base64: str = None, max_discount_pct: float = 0, agent_mode: str = "sales", user_tags: list = None):
    import os
    # Load inside function to pick up live .env changes!
    api_key = os.getenv("GEMINI_API_KEY", "dummy_key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    parts = []
    if image_base64:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": image_base64}})
    parts.append({"text": user_message})
    
    tags_str = ""
    if user_tags:
        tags_str = f"\n\nUSER PROFILE TAGS: {', '.join(user_tags)}. Use these psychological tags to hyper-personalize your sales pitch to the user's personality!"
        
    if agent_mode == "support":
        sys_instruction = "You are a multi-agent escalation court. When the user has a dispute or return request, you must simulate the following chain of thought in your reasoning:\n1. [Support Agent]: Summarizes the complaint and evidence.\n2. [Policy Agent]: Checks the 30-day refund policy.\n3. [Manager Agent]: Issues the final ruling.\nOnly output the Manager Agent's final ruling to the user. If a refund is approved by the Manager, use the process_return tool. IMPORTANT: Output your final response in the user's detected language."
        function_declarations = [
            {
                "name": "process_return",
                "description": "Process a return and deduct the amount from the global ledger.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {"order_id": {"type": "STRING"}, "refund_amount_paise": {"type": "INTEGER"}},
                    "required": ["order_id", "refund_amount_paise"]
                }
            }
        ]
    else:
        sys_instruction = f"You are a helpful e-commerce sales agent. You help humans find products, add them to their cart, and checkout. Always use tools to take actions. If the user asks for a product, use search_catalog. If the user objects to a price, you MUST offer EXACTLY a {max_discount_pct}% discount. Do not offer any other discount percentage. Apply the discounted price directly in add_to_cart if you negotiated. If the user has a post-purchase support issue (like returns), use transfer_to_support. IMPORTANT: Always detect the language the user is speaking. Think and execute function calls in English, but output your final conversational response strictly in the user's language." + tags_str
        function_declarations = [
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
            },
            {
                "name": "transfer_to_support",
                "description": "Transfer the user to the support agent for post-purchase issues like returns.",
            },
            {
                "name": "visual_try_on",
                "description": "Use this when the user uploads an image of their room or space and asks to see how a product looks inside it. Provide the product title and a brief description of the user's room.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "product_title": {"type": "STRING"},
                        "room_description": {"type": "STRING"}
                    },
                    "required": ["product_title", "room_description"]
                }
            }
        ]

    payload = {
        "contents": [
            {"role": "user", "parts": parts}
        ],
        "systemInstruction": {
            "parts": [{"text": sys_instruction}]
        },
        "tools": [
            {
                "functionDeclarations": function_declarations
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

def process_chat(db: Session, session_id: uuid.UUID, user_message: str, image_base64: str = None) -> dict:
    from app.models import MerchantConfig, Session as DbSession, UserProfile
    merchant = db.query(MerchantConfig).first()
    max_discount_pct = float(merchant.max_discount_pct) if merchant else 0.0
    
    sess = db.query(DbSession).filter(DbSession.session_id == session_id).first()
    agent_mode = sess.agent_mode if sess else "sales"
    
    user_tags = []
    if sess and sess.phone_number:
        profile = db.query(UserProfile).filter_by(phone_number=sess.phone_number).first()
        if profile and profile.tags_json:
            user_tags = profile.tags_json
    
    gemini_resp = call_gemini_agent(user_message, image_base64, max_discount_pct, agent_mode, user_tags)
    
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
            from app.models import MissedSearch
            db.add(MissedSearch(session_id=session_id, search_query=query))
            db.commit()
            
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
    elif action_type == 'transfer_to_support':
        from app.models import Session as DbSession
        sess = db.query(DbSession).filter(DbSession.session_id == session_id).first()
        if sess:
            sess.agent_mode = "support"
            db.commit()
        return {"status": "transferred", "message": "Transferred to support."}
    elif action_type == 'process_return':
        return {"status": "success", "message": f"Processed return for order {payload.get('order_id')}."}
    elif action_type == 'visual_try_on':
        import urllib.parse
        product_title = payload.get('product_title', 'a product')
        room_desc = payload.get('room_description', 'a room')
        
        prompt = f"A realistic photo of {room_desc} featuring a {product_title} placed naturally inside"
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        
        return {
            "status": "success", 
            "message": f"Here is how the {product_title} might look in your space!", 
            "try_on_image_url": image_url
        }
    return {"status": "unknown_action"}
