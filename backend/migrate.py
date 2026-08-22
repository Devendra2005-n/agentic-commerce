from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE sessions ADD COLUMN chat_history JSONB NOT NULL DEFAULT '[]'::jsonb"))
        conn.commit()
        print("Column added")
    except Exception as e:
        print("Error or already exists:", e)
