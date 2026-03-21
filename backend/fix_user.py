from models import SessionLocal, init_db
from models.user import User

db = SessionLocal()
try:
    if not db.query(User).filter(User.id == 1).first():
        print("Creating User ID 1...")
        new_user = User(id=1, username="test_mcp_user", password="password")
        db.add(new_user)
        db.commit()
        print("Created successfully!")
    else:
        print("User 1 already exists.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
