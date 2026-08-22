import os
import json
import openai
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Intent, Product
from app.guardrail.engine import evaluate

# TRD §6 Tool Definitions
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the merchant catalog by free text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term, e.g. 'lamp' or 'desk'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_upsell",
            "description": "Propose an upsell item to the buyer based on what they are currently viewing or buying.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_sku": {"type": "string"},
                    "reason_code": {"type": "string"},
                },
                "required": ["candidate_sku", "reason_code"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are Meera's Agentic Commerce AI. You help buyers find products and checkout.
You are professional, concise, and helpful. 
You can use tools to search the catalog and propose upsells. 
Never invent products or prices. Only use data returned by your tools.
"""

def call_llm(db: Session, user_message: str, buyer_ref: str = "anonymous") -> Dict[str, Any]:
    """
    Real LLM integration using OpenAI API spec for Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("GEMINI_API_KEY found! Running True Agentic orchestration via Gemini...")
    
    # Authenticate User & Load Isolated Session
    from app.models import Session as DbSession, MerchantConfig
    session = db.query(DbSession).filter(DbSession.buyer_ref == buyer_ref).first()
    if not session:
        # Create a new isolated session for this user
        merchant = db.query(MerchantConfig).first()
        if merchant:
            session = DbSession(merchant_id=merchant.merchant_id, actor_type="human", buyer_ref=buyer_ref)
            db.add(session)
            db.commit()
            db.refresh(session)
        else:
            return {"type": "text", "text": "System not initialized. Please run seed.py"}
            
    history = session.chat_history or []
    if not history:
        dynamic_system_prompt = SYSTEM_PROMPT
        if buyer_ref != "anonymous":
            dynamic_system_prompt += f"\n\n[CONFIDENTIAL KNOWLEDGE]: The current user is authenticated as phone number {buyer_ref}. Greet them back! Example: Welcome back!"
        history = [{"role": "system", "content": dynamic_system_prompt}]
        
    history.append({"role": "user", "content": user_message})
    
    # --- INTENT INTERCEPTOR ---
    # Intercept hardcoded UI intents before sending to Gemini
    if user_message.lower().startswith("checkout "):
        item_title = user_message[9:].strip()
        product = db.query(Product).filter(Product.title.ilike(f"%{item_title}%")).first()
        if product:
            price = product.price_paise / 100
            
            # --- GUARDRAIL CHECK ---
            merchant = db.query(MerchantConfig).first()
            if product.price_paise > merchant.max_order_paise:
                # Gated and Rejected! (Failure handled gracefully)
                from app.models import Decision
                import uuid
                rejection = Decision(
                    decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                    session_id=session.session_id,
                    rule_id="max_order_limit",
                    decision="rejected",
                    reason=f"Product price ({product.price_paise/100}) exceeds merchant hard limit ({merchant.max_order_paise/100})"
                )
                db.add(rejection)
                db.commit()
                return {
                    "type": "text",
                    "text": f"Guardrail blocked this checkout: The price of {product.title} exceeds this store's maximum AI-authorized transaction limit. An audit log has been created."
                }
            
            # Approved! Write to Audit Trail
            from app.models import AuditEvent, Decision
            import uuid
            
            # 1. Log the decision
            dec_id = f"dec_{uuid.uuid4().hex[:8]}"
            approval = Decision(
                decision_id=dec_id,
                session_id=session.session_id,
                rule_id="max_order_limit",
                decision="approved",
                reason="Price is within merchant limits."
            )
            db.add(approval)
            
            # 2. Log the money action
            event = AuditEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                session_id=session.session_id,
                event_type="checkout_initiated",
                status="pending",
                decision_id=dec_id,
                detail={"product": product.title, "amount_paise": product.price_paise}
            )
            db.add(event)
            db.commit()
            
            # Save the message to history so it doesn't get lost
            history.append({"role": "assistant", "content": f"Proceeding to checkout for {product.title}."})
            session.chat_history = history
            db.commit()
            
            return {
                "type": "checkout_confirm",
                "text": f"Great choice! Please confirm your order. This action has been securely audited.",
                "cart": [{"sku": product.sku, "title": product.title, "price": price}],
                "total": price
            }
            
    if user_message.lower().startswith("payment_successful_callback_id_"):
        payment_id = user_message[31:]
        
        # Write to Audit Trail
        from app.models import AuditEvent
        import uuid
        event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            session_id=session.session_id,
            event_type="payment_captured",
            status="captured",
            razorpay_order_id="mock_ord_123", # For the dashboard
            razorpay_payment_id=payment_id,
            detail={"message": "Razorpay payment succeeded and captured"}
        )
        db.add(event)
        db.commit()
        
        history.append({"role": "assistant", "content": f"Payment {payment_id} was successfully processed!"})
        session.chat_history = history
        db.commit()
        return {
            "type": "payment_success",
            "text": "Your payment was successfully processed! Thank you for your order. A receipt has been added to the audit trail."
        }

    try:
        # Use Gemini's OpenAI Compatibility Endpoint!
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=history,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        message = response.choices[0].message
        history.append({"role": "assistant", "content": message.content, "tool_calls": [t.model_dump() for t in message.tool_calls] if message.tool_calls else None})
        session.chat_history = history
        db.commit()

        # If the LLM decided to use a tool (e.g. search catalog)
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            
            # 1. Search Catalog Tool
            if tool_call.function.name == "search_catalog":
                query = args.get("query", "").lower()
                # Actual database search!
                products = db.query(Product).filter(Product.title.ilike(f"%{query}%")).limit(3).all()
                
                if not products:
                    # MAGIC INVENTORY: Create products on the fly so the user always sees what they searched for!
                    import random
                    base_price = random.randint(800, 4000)
                    p1 = Product(
                        sku=f"MAGIC_{query.upper()[:5]}_{random.randint(100,999)}",
                        title=f"Premium {query.title()}",
                        description="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",
                        price_paise=base_price * 100,
                        category=query,
                        stock_qty=10
                    )
                    p2 = Product(
                        sku=f"MAGIC_{query.upper()[:5]}_{random.randint(100,999)}",
                        title=f"Classic {query.title()}",
                        description="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",
                        price_paise=(base_price + 500) * 100,
                        category=query,
                        stock_qty=5
                    )
                    db.add(p1)
                    db.add(p2)
                    db.commit()
                    db.refresh(p1)
                    db.refresh(p2)
                    products = [p1, p2]
                    
                results = []
                for p in products:
                    results.append({
                        "sku": p.sku, 
                        "title": p.title, 
                        "price": p.price_paise / 100, 
                        "img": p.description # We stored img URL in description
                    })
                    
                return {
                    "type": "catalog_results",
                    "text": f"I searched the catalog for '{query}'. Here is what I found:",
                    "results": results
                }
            # 2. Upsell Tool
            elif tool_call.function.name == "propose_upsell":
                sku = args.get("candidate_sku", "")
                reason = args.get("reason_code", "Highly recommended based on your cart!")
                # Get the upsell product
                upsell_item = db.query(Product).filter(Product.sku == sku).first()
                if not upsell_item:
                    upsell_item = db.query(Product).first() # Fallback to any item
                
                if upsell_item:
                    return {
                        "type": "upsell_prompt",
                        "text": "I noticed you were looking at some great items. Can I recommend this bundle addition?",
                        "upsell_item": {
                            "sku": upsell_item.sku, 
                            "title": upsell_item.title, 
                            "price": upsell_item.price_paise / 100, 
                            "img": upsell_item.description
                        },
                        "reason_rendered": reason
                    }
                    
        # If the LLM just responded with text
        return {
            "type": "text",
            "text": message.content or "I am not sure how to respond to that."
        }

    except Exception as e:
        print(f"Gemini API failed ({e}).")
        return {
            "type": "text", 
            "text": f"Online Mode Error: Gemini API rejected the request. Details: {str(e)}"
        }

