
import pandas as pd
import numpy as np
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Equipment, Intervention, InterventionStatus
from app.services.kpi_service import KPIService

# ML Libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from prophet import Prophet
import joblib

# Optional XGBoost
try:
    import xgboost as xgb
except ImportError:
    xgb = None

logger = logging.getLogger(__name__)

class PredictionService:
    """
    AI Forecast Service for Predictive Maintenance.
    Uses generic ML models (Random Forest, XGBoost) and Time Series models (Prophet)
    to predict RUL, MTBF/MTTR trends, and next failure dates.
    """

    @staticmethod
    def _fetch_equipment_history(db: Session, equipment_id: int) -> pd.DataFrame:
        """
        Fetch intervention history for an equipment and convert to DataFrame.
        """
        interventions = db.query(Intervention).filter(
            Intervention.equipment_id == equipment_id,
            Intervention.status == InterventionStatus.COMPLETED
        ).order_by(Intervention.date_intervention.asc()).all()

        if not interventions:
            return pd.DataFrame()

        data = []
        for i in interventions:
            data.append({
                'date': i.date_intervention,
                'downtime': i.duree_arret or 0,
                'type_panne': i.type_panne,
                'cost': i.cout_total or 0,
                'is_failure': 1 if i.type_panne not in ['Preventive', 'Préventif'] else 0
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        return df

    @staticmethod
    def _prepare_time_series_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from raw intervention data for RUL/failure prediction.
        Target: Days until next failure (RUL for specific point in time).
        """
        if df.empty or len(df) < 5:
            return pd.DataFrame()

        # Filter for only failures if we are predicting failure RUL
        # But we might want to include preventive maintenance as features
        
        # Calculate Time Between Failures (TBF)
        df = df.sort_values('date')
        df['days_since_last_event'] = df['date'].diff().dt.days.fillna(0)
        
        # Rolling features
        df['rolling_downtime_3'] = df['downtime'].rolling(window=3).mean()
        df['rolling_cost_3'] = df['cost'].rolling(window=3).mean()
        df['cumulative_failures'] = df['is_failure'].cumsum()
        
        # Target: Days until NEXT failure (for RUL prediction)
        # We need to shift the date backward. 
        # T_{next} - T_{current}
        df['next_failure_date'] = df[df['is_failure'] == 1]['date'].shift(-1)
        df['days_to_next_failure'] = (df['next_failure_date'] - df['date']).dt.days
        
        # Drop rows where we don't know the next failure (the last ones)
        # For training, we drop na. For inference, we use the model.
        train_df = df.dropna(subset=['days_to_next_failure']).copy()
        
        # Additional features
        train_df['month'] = train_df['date'].dt.month
        train_df['day_of_week'] = train_df['date'].dt.dayofweek
        
        return train_df.fillna(0)

    @staticmethod
    def train_and_predict_rul(db: Session, equipment_id: int) -> Dict:
        """
        Train models to predict Remaining Useful Life (Days until next failure).
        Uses 'Smart Selection' to pick best model between RF and XGBoost.
        """
        try:
            df = PredictionService._fetch_equipment_history(db, equipment_id)
            if df.empty or len(df) < 10:
                return {
                    "error": "Insufficient data for prediction (minimum 10 records required)",
                    "rul_days": None,
                    "confidence": 0
                }

            train_df = PredictionService._prepare_time_series_features(df)
            if train_df.empty:
                 return {
                    "error": "Could not generate features features from data",
                    "rul_days": None,
                    "confidence": 0
                }

            features = ['days_since_last_event', 'rolling_downtime_3', 'rolling_cost_3', 'cumulative_failures', 'month', 'day_of_week']
            X = train_df[features]
            y = train_df['days_to_next_failure']

            # Train/Test Split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            models = {}
            metrics = {}

            # 1. Random Forest
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X_train, y_train)
            pred_rf = rf.predict(X_test)
            rmse_rf = np.sqrt(mean_squared_error(y_test, pred_rf))
            models['RandomForest'] = rf
            metrics['RandomForest'] = rmse_rf

            # 2. XGBoost (if available)
            if xgb:
                xg_reg = xgb.XGBRegressor(objective ='reg:squarederror', n_estimators=100)
                xg_reg.fit(X_train, y_train)
                pred_xg = xg_reg.predict(X_test)
                rmse_xg = np.sqrt(mean_squared_error(y_test, pred_xg))
                models['XGBoost'] = xg_reg
                metrics['XGBoost'] = rmse_xg

            # Smart Selection: Best RMSE
            best_model_name = min(metrics, key=metrics.get)
            best_model = models[best_model_name]
            logger.info(f"Selected Best Model for Equipment {equipment_id}: {best_model_name} (RMSE: {metrics[best_model_name]:.2f})")

            # Predict RUL for Current State (The last record in original DF)
            last_state = df.iloc[-1:].copy()
            
            # Re-calc temporal features for last state relative to NOW if date is old? 
            # Or just use the last known event properties.
            # We need to construct the features vector for the 'current' moment.
            # Ideally we take the last event, and 'days_since_last_event' is (Now - Last Event Date).
            
            current_date = pd.to_datetime(date.today())
            last_event_date = last_state['date'].iloc[0]
            days_since = (current_date - last_event_date).days
            
            # Prepare input vector
            input_features = pd.DataFrame([{
                'days_since_last_event': days_since,
                'rolling_downtime_3': df['downtime'].rolling(window=3).mean().iloc[-1] or 0,
                'rolling_cost_3': df['cost'].rolling(window=3).mean().iloc[-1] or 0,
                'cumulative_failures': df['is_failure'].sum(),
                'month': current_date.month,
                'day_of_week': current_date.dayofweek
            }])
            
            predicted_rul = best_model.predict(input_features)[0]
            
            # Probability of failure in next 30 days?
            # Confidence based on Normalized RMSE (NRMSE) using the mean of target variable (average cycle time)
            # This prevents 0% confidence when predicted RUL is small but error is normal.
            mean_cycle_time = y.mean() if not y.empty and y.mean() > 0 else 1
            nrmse = metrics[best_model_name] / mean_cycle_time
            confidence = max(0, min(100, (1 - nrmse) * 100))
            
            return {
                "predicted_rul_days": round(float(predicted_rul), 2),
                "predicted_failure_date": (current_date + timedelta(days=float(predicted_rul))).strftime('%Y-%m-%d'),
                "model_used": str(best_model_name),
                "rmse_accuracy": round(float(metrics[best_model_name]), 2),
                "confidence_score": round(float(confidence), 2)
            }
        except Exception as e:
            logger.error(f"Error in RUL prediction: {str(e)}", exc_info=True)
            return {
                "error": f"Prediction failed: {str(e)}",
                "rul_days": None,
                "confidence": 0
            }

    @staticmethod
    def forecast_mtbf_trend(db: Session, equipment_id: int, horizon_days: int = 90) -> Dict:
        """
        Forecast MTBF trend using Prophet.
        This models the changing reliability of the machine over time.
        """
        try:
            # We need time series of MTBF. 
            # We can calculate MTBF on a broader window (monthly) and forecast that.
                # Strategy: Forecast "Time Between Failures" (TBF) based on event history
            # This is more accurate than monthly aggregation for sparse data (e.g. failures every 45 days)
            
            df = PredictionService._fetch_equipment_history(db, equipment_id)
            if df.empty or len(df) < 4:
                 return {"error": "Insufficient data (need at least 4 failures)"}
            
            # Calculate TBF (days since previous failure)
            df = df.sort_values('date')
            df['tbf'] = df['date'].diff().dt.days
            
            # Drop the first record (NaN TBF) and any anomalies (TBF=0)
            df_prophet = df.dropna(subset=['tbf'])
            df_prophet = df_prophet[df_prophet['tbf'] > 0]
            
            if len(df_prophet) < 3:
                return {"error": "Insufficient valid intervals for forecasting"}

            # Prepare for Prophet: ds=date of event, y=TBF leading up to it
            # We want to predict: At future date X, what will be the TBF?
            # Actually, Prophet predicts y given ds.
            # So we effectively model: "Trend of TBF over time".
            prophet_df = df_prophet[['date', 'tbf']].rename(columns={'date': 'ds', 'tbf': 'y'})
            
            # Fit Prophet
            # MCMC samples can be slow, so we use defaults.
            # Using logistic growth might be better if we knew max TBF, but linear is fine for trends.
            m = Prophet(seasonality_mode='multiplicative', daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False)
            m.fit(prophet_df)
            
            # Forecast
            # we want to see the trend for next horizon
            future = m.make_future_dataframe(periods=int(horizon_days/30), freq='M') 
            # Note: Prophet freq='M' is month end.
            
            forecast = m.predict(future)
            
            # Format
            forecast_data = []
            for _, row in forecast.iterrows():
                # We convert "Days" TBF to "Hours" MTBF for consistency with UI (MTBF usually in hours)
                # Or we keep it in Days and update UI label. 
                # The UI says "MTBF (Hours)". So let's convert days -> hours.
                predicted_hours = float(row['yhat']) * 24
                lower_hours = float(row['yhat_lower']) * 24
                upper_hours = float(row['yhat_upper']) * 24
                
                # Cap at 0
                predicted_hours = max(0, predicted_hours)
                lower_hours = max(0, lower_hours)
                upper_hours = max(0, upper_hours)
                
                forecast_data.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_mtbf": round(predicted_hours, 2),
                    "lower_bound": round(lower_hours, 2),
                    "upper_bound": round(upper_hours, 2)
                })
                
            return {
                "forecast": forecast_data[-6:], # Return last 6 points (mix of history/future)
                "model": "Prophet (TBF Trend)"
            }
        except Exception as e:
            logger.error(f"Error in MTBF forecast: {str(e)}", exc_info=True)
            # Return empty forecast structure rather than error object to avoid frontend crash if handled poorly, 
            # or keep error and ensure frontend handles it. 
            # Given previous frontend fix, returning error string is fine, but let's make it descriptive.
            return {"error": f"Forecast unavailable: {str(e)}. (Requires >2 months of data)"}

    @staticmethod
    def get_full_forecast(db: Session, equipment_id: int) -> Dict:
        """
        Aggregates RUL prediction and MTBF forecast.
        """
        rul_data = PredictionService.train_and_predict_rul(db, equipment_id)
        mtbf_data = PredictionService.forecast_mtbf_trend(db, equipment_id)
        
        # Predicted Downtime = (Horizon / Integrated MTBF) * MTTR_current
        # Simple estimation:
        mttr_stats = KPIService.calculate_mttr(db, equipment_id=equipment_id)
        avg_mttr = mttr_stats.get('mttr_hours', 0) or 0
        
        predicted_downtime_next_month = 0
        if rul_data.get('predicted_rul_days'):
            # If failure is within 30 days, we expect 1 MTTR of downtime
            if rul_data['predicted_rul_days'] < 30:
                predicted_downtime_next_month = avg_mttr
        
        return {
            "equipment_id": equipment_id,
            "rul": rul_data,
            "mtbf_forecast": mtbf_data,
            "predicted_downtime_30d": predicted_downtime_next_month,
            "current_mttr": avg_mttr
        }
