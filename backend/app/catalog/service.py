from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Product

def search_catalog(db: Session, query: str, max_price_paise: int = None, tags: list = None):
    stmt = db.query(Product).filter(
        or_(
            Product.title.ilike(f"%{query}%"),
            Product.description.ilike(f"%{query}%"),
            Product.category.ilike(f"%{query}%")
        )
    )
    if max_price_paise is not None:
        stmt = stmt.filter(Product.price_paise <= max_price_paise)
    if tags:
        for tag in tags:
            stmt = stmt.filter(Product.style_tags.any(tag))
    
    return stmt.all()

def get_product(db: Session, sku: str):
    return db.query(Product).filter(Product.sku == sku).first()
