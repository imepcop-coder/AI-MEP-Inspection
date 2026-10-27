from app.database.db import SessionLocal
from app.models.user import User
from app.auth.security import hash_password

db = SessionLocal()

user = db.query(User).filter(User.email == "admin@aimep.com").first()

if user:
    user.password = hash_password("Admin@123")
    db.commit()
    print("Password reset successfully!")
    print("Email: admin@aimep.com")
    print("Password: Admin@123")
else:
    print("User not found!")

db.close()