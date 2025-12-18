# seed_demo.py
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from models_core import get_session, User  # adjust to models.py if needed

def main():
    s = get_session()
    print(f"DB URL: {s.bind.url}")

    # Check if demo user exists
    user = s.query(User).filter_by(email="demo@demo.com").first()
    if not user:
        user = User(
            email="demo@demo.com",
            password_hash=generate_password_hash("Demo123!"),
            # add this only if your User model has a created_at column
            created_at=datetime.now(timezone.utc) if hasattr(User, "created_at") else None,
        )
        s.add(user)
        s.commit()
        print("Created demo user: demo@demo.com / Demo123!")
    else:
        print("ℹ Demo user already exists — no action needed.")

    s.close()
    print("Demo seed complete (user only).")

if __name__ == "__main__":
    main()
