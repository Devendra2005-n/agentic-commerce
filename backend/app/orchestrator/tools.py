# LLM Tool Schemas matching the TRD
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the merchant's catalog for products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_price_paise": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": "View current cart contents.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add an item to the buyer's cart. You must provide the exact SKU and price_paise from the catalog to prevent drift.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string"},
                    "qty": {"type": "integer"},
                    "price_paise": {"type": "integer"}
                },
                "required": ["sku", "qty", "price_paise"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Initiate checkout for the current cart, generating a Razorpay order and payment link.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_payment_status",
            "description": "Check if the buyer has paid the pending order.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
    # propose_upsell and cancel_order will be added in Phase 5 and 8
]
