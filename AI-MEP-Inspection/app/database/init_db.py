from sqlalchemy.orm import Session

from app.database.db import Base, engine, SessionLocal
from app.auth.security import hash_password
from app.models.report_template import ReportTemplate
from app.models.user import User

Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

admin = db.query(User).filter(
    User.email == "admin@aimep.com"
).first()

if not admin:

    admin = User(
        full_name="System Administrator",
        email="admin@aimep.com",
        password=hash_password("Admin@123"),
        role="Super Admin"
    )

    db.add(admin)
    db.commit()

    print("✅ Default Admin Created")

else:

    print("✅ Admin Already Exists")

db.close()
