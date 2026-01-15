# scripts/debug_data.py
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

os.environ['DATABASE_URL'] = 'postgresql://gmao_user:gmao_password@localhost:5432/gmao_db'

from app.database import SessionLocal
from app.models import Intervention
from sqlalchemy import func, text
from datetime import datetime, timedelta

def debug_interventions_data():
    db = SessionLocal()
    
    try:
        # Count total interventions
        total_count = db.query(func.count(Intervention.id)).scalar()
        print(f"Total interventions in database: {total_count}")
        
        # Check date range
        min_date = db.query(func.min(Intervention.date_intervention)).scalar()
        max_date = db.query(func.max(Intervention.date_intervention)).scalar()
        print(f"Date range: {min_date} to {max_date}")
        
        # Check recent data (last 90 days)
        cutoff_date = datetime.now().date() - timedelta(days=90)
        recent_count = db.query(func.count(Intervention.id)).filter(
            Intervention.date_intervention >= cutoff_date
        ).scalar()
        print(f"Interventions in last 90 days: {recent_count}")
        
        # Check if date_intervention is NULL
        null_dates = db.query(func.count(Intervention.id)).filter(
            Intervention.date_intervention.is_(None)
        ).scalar()
        print(f"Interventions with NULL date_intervention: {null_dates}")
        
        # Check equipment_id distribution
        equipment_counts = db.query(
            Intervention.equipment_id, 
            func.count(Intervention.id)
        ).group_by(Intervention.equipment_id).all()
        print(f"Equipment distribution: {equipment_counts[:10]}")  # First 10
        
        # Sample some records
        sample_records = db.query(Intervention).limit(5).all()
        print("\nSample records:")
        for record in sample_records:
            print(f"  ID: {record.id}, Equipment: {record.equipment_id}, Date: {record.date_intervention}, Duration: {record.duree_arret}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_interventions_data()