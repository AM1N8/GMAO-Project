
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Equipment, Intervention, InterventionStatus, EquipmentStatus

def seed_data():
    db = SessionLocal()
    try:
        print("Creating synthetic data for AI Forecast...")
        
        # 1. Create or Get Equipment
        eq = db.query(Equipment).filter(Equipment.designation == "Hydraulic Pump X-200").first()
        if not eq:
            eq = Equipment(
                designation="Hydraulic Pump X-200",
                # code="PUMP-X200-TEST", # Invalid
                serial_number="PUMP-X200-TEST",
                type="Pump",
                location="Sector A",
                status=EquipmentStatus.ACTIVE,
                acquisition_date=datetime.now().date() - timedelta(days=730), # 2 years ago
                manufacturer="Industrial Pumps Inc.",
                model="X-200"
            )
            db.add(eq)
            db.commit()
            db.refresh(eq)
            print(f"Created equipment: {eq.designation} (ID: {eq.id})")
        else:
            print(f"Using existing equipment: {eq.designation} (ID: {eq.id})")

        # 2. Clear existing interventions for this equipment to ensure clean history
        # db.query(Intervention).filter(Intervention.equipment_id == eq.id).delete()
        # db.commit()
        
        # 3. Generate History (Last 3 years) with a stable pattern
        # Pattern: Machine fails regularly around every 42-48 days (Stable MTBF)
        start_date = datetime.now().date() - timedelta(days=1000)
        current_date = start_date
        
        count = 0
        while current_date < datetime.now().date():
            # More consistent interval (42 to 48 days) -> Low variance, easier to learn
            days_to_next = random.randint(42, 48)
            current_date += timedelta(days=days_to_next)
            
            if current_date >= datetime.now().date():
                break
                
            # Create Intervention (Failure)
            # Downtime also fairly consistent
            downtime = random.randint(4, 12) 
            cost = random.randint(800, 1200)
            
            intervention = Intervention(
                equipment_id=eq.id,
                date_intervention=current_date,
                type_panne="Mechanical Failure",
                resume_intervention=f"Scheduled bearing replacement due to wear (Cycle {count+1})",
                status=InterventionStatus.COMPLETED,
                duree_arret=downtime,
                cout_total=cost,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(intervention)
            count += 1
            
        print(f"Generated {count} high-quality history records for stable model training.")
        
        db.commit()
        print(f"Successfully added {count} synthetic interventions for equipment {eq.id}.")
        print("You can now select 'Hydraulic Pump X-200' in the AI Forecast dashboard.")
            
        db.commit()
        print(f"Successfully added {count} synthetic interventions for equipment {eq.id}.")
        print("You can now select 'Hydraulic Pump X-200' in the AI Forecast dashboard.")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
