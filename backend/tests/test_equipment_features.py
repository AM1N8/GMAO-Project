import os
import sys
from pathlib import Path

os.environ['DATABASE_URL'] = 'postgresql://gmao_user:gmao_password@localhost:5432/gmao_db'
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.ml.feature_engineering import FeatureEngineer

def test_equipment_features():
    db = SessionLocal()
    
    try:
        print("Testing equipment features with type conversion...")
        
        # Test the full pipeline
        df, targets = FeatureEngineer.create_full_feature_set(db, lookback_days=None)
        
        print(f"✅ Success! Features shape: {df.shape}")
        print(f"✅ Equipment features created: {[col for col in df.columns if 'equipment' in col]}")
        print(f"✅ Targets: {list(targets.keys())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_equipment_features()