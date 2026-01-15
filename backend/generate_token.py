from app.database import SessionLocal
from app.models import Technician, TechnicianStatus
from jose import jwt
import os
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
email = "theabyssswatcher@gmail.com"
try:
    # 1. Ensure User Exists
    user = db.query(Technician).filter(Technician.email == email).first()
    if not user:
        print(f"User {email} not found. Creating...")
        user = Technician(
            nom="Admin",
            prenom="User",
            email=email,
            specialite="System Admin",
            status=TechnicianStatus.ACTIVE,
            matricule="ADM001"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("User created.")
    else:
        print("User found.")

    # 2. Generate Token
    SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
    ALGORITHM = "HS256"
    
    payload = {
        "email": email,
        "sub": str(user.id),
        "role": "authenticated", # Standard Supabase claim
        "app_metadata": {"provider": "email"},
        "user_metadata": {"full_name": "Admin User"}
    }
    
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    with open("token.txt", "w") as f:
        f.write(token)
    print("Token written to token.txt")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
