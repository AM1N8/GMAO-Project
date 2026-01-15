
from app.database import SessionLocal
from app.models import Equipment, Intervention, FailureMode, RPNAnalysis
from sqlalchemy import text

db = SessionLocal()
try:
    print(f"Equipment: {db.query(Equipment).count()}")
    print(f"Interventions: {db.query(Intervention).count()}")
    print(f"FailureModes: {db.query(FailureMode).count()}")
    print(f"RPNAnalysis: {db.query(RPNAnalysis).count()}")
    
    # Check a sample equipment
    eq = db.query(Equipment).first()
    if eq:
        print(f"Sample Equipment: {eq.designation}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
