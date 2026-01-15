"""
ML Model Training Script
Run this script to train all ML models on your historical data

Usage:
    python train_ml_models.py --kpi mttr --equipment-id 1
    python train_ml_models.py --kpi all
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Set PostgreSQL database URL before importing any database modules
os.environ['DATABASE_URL'] = 'postgresql://gmao_user:gmao_password@localhost:5432/gmao_db'

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.ml.prediction_service import prediction_service
from app.ml.model_manager import model_manager
from app.ml.logger import logger
import time


def check_database_connection():
    """Verify we're connecting to PostgreSQL"""
    from app.database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            logger.info(f"Connected to: {db_version}")
            
            # Check if interventions table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'interventions'
                );
            """))
            table_exists = result.scalar()
            logger.info(f"Interventions table exists: {table_exists}")
            
            if not table_exists:
                logger.error("Interventions table not found in database!")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def train_kpi_models(
    kpi_type: str,
    equipment_id: int = None,
    models: list = None
):
    """Train models for a specific KPI"""
    
    logger.info(f"=" * 70)
    logger.info(f"TRAINING MODELS FOR KPI: {kpi_type.upper()}")
    logger.info(f"Equipment Filter: {equipment_id or 'All'}")
    logger.info(f"=" * 70)
    
    # Verify database connection first
    if not check_database_connection():
        raise Exception("Database connection failed - cannot proceed with training")
    
    db = SessionLocal()
    
    try:
        # Initialize prediction service
        if not prediction_service.is_initialized:
            prediction_service.initialize()
        
        # Train models
        start_time = time.time()
        
        results = prediction_service.train_models(
            db=db,
            kpi_type=kpi_type,
            equipment_id=equipment_id,
            models_to_train=models
        )
        
        duration = time.time() - start_time
        
        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("TRAINING COMPLETED")
        logger.info("=" * 70)
        
        logger.info(f"\nData Summary:")
        logger.info(f"  Train samples: {results['data_summary']['train_samples']}")
        logger.info(f"  Val samples: {results['data_summary']['val_samples']}")
        logger.info(f"  Test samples: {results['data_summary']['test_samples']}")
        logger.info(f"  Features: {len(results['data_summary']['features'])}")
        
        logger.info(f"\nTraining Results:")
        for model_name, metrics in results['training_results'].items():
            if 'error' in metrics:
                logger.error(f"  {model_name}: FAILED - {metrics['error']}")
            else:
                val_mae = metrics.get('val_mae', metrics.get('train_mae', 'N/A'))
                logger.info(f"  {model_name}: MAE = {val_mae:.2f}")
        
        logger.info(f"\nTest Results:")
        for model_name, metrics in results['test_results'].items():
            if 'error' in metrics:
                logger.error(f"  {model_name}: FAILED - {metrics['error']}")
            else:
                logger.info(
                    f"  {model_name}: MAE = {metrics['mae']:.2f}, "
                    f"RMSE = {metrics['rmse']:.2f}, "
                    f"R² = {metrics['r2']:.3f}"
                )
        
        logger.success(f"\nBest Model: {results['best_model']}")
        logger.info(f"Total Training Time: {duration:.2f}s")
        logger.info("=" * 70)
        
        return results
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Train ML models for KPI prediction'
    )
    
    parser.add_argument(
        '--kpi',
        type=str,
        default='mttr',
        choices=['mttr', 'mtbf', 'availability', 'all'],
        help='KPI type to train models for'
    )
    
    parser.add_argument(
        '--equipment-id',
        type=int,
        default=None,
        help='Train on specific equipment only'
    )
    
    parser.add_argument(
        '--models',
        type=str,
        nargs='+',
        default=None,
        choices=['svr', 'random_forest', 'xgboost', 'prophet', 'sarima'],
        help='Specific models to train (default: all)'
    )
    
    args = parser.parse_args()
    
    # Log database info
    db_url = os.environ.get('DATABASE_URL', 'Not set')
    logger.info(f"Database URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    if args.kpi == 'all':
        kpis = ['mttr', 'mtbf', 'availability']
    else:
        kpis = [args.kpi]
    
    logger.info("\n" + "=" * 70)
    logger.info("ML MODEL TRAINING SCRIPT")
    logger.info("=" * 70)
    logger.info(f"KPIs to train: {', '.join(kpis)}")
    logger.info(f"Equipment filter: {args.equipment_id or 'All'}")
    logger.info(f"Models: {args.models or 'All'}")
    logger.info("=" * 70 + "\n")
    
    all_results = {}
    
    for kpi in kpis:
        try:
            results = train_kpi_models(
                kpi_type=kpi,
                equipment_id=args.equipment_id,
                models=args.models
            )
            all_results[kpi] = results
            
            # Small delay between KPIs
            if len(kpis) > 1:
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Failed to train models for {kpi}: {e}")
            all_results[kpi] = {'error': str(e)}
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("ALL TRAINING COMPLETED")
    logger.info("=" * 70)
    
    for kpi, results in all_results.items():
        if 'error' in results:
            logger.error(f"  {kpi.upper()}: FAILED")
        else:
            logger.success(f"  {kpi.upper()}: SUCCESS - Best model: {results['best_model']}")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    main()