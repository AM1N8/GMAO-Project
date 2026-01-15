"""
data_finetune/utils/data_loader.py

Utility to load and preprocess GMAO datasets.
"""

import pandas as pd
from pathlib import Path
from typing import Tuple


class DataLoader:
    """Load and preprocess GMAO datasets."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
    
    def load_amdec(self) -> pd.DataFrame:
        """Load AMDEC dataset."""
        file_path = self.data_path / "GMAO_integrator_clean.csv"
        df = pd.read_csv(file_path, encoding='latin-1')
        
        # Convert date columns
        date_cols = ['Date intervention', 'Date demande']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # Clean numeric columns
        if 'Durée arrêt (h)' in df.columns:
            df['Durée arrêt (h)'] = pd.to_numeric(df['Durée arrêt (h)'], errors='coerce')
        if 'Coût matériel' in df.columns:
            df['Coût matériel'] = pd.to_numeric(df['Coût matériel'], errors='coerce')
        
        return df
    
    def load_dispo(self) -> pd.DataFrame:
        """Load Dispo MTBF/MTTR dataset."""
        file_path = self.data_path / "AMDEC_clean.csv"
        df = pd.read_csv(file_path, encoding='latin-1')
        
        # Convert date columns
        if 'Date intervention' in df.columns:
            df['Date intervention'] = pd.to_datetime(df['Date intervention'], errors='coerce', dayfirst=True)
        
        # Clean numeric columns
        numeric_cols = ['Durée arrêt (h)', 'Coût matériel']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def load_workload(self) -> pd.DataFrame:
        """Load Workload dataset."""
        file_path = self.data_path / "Workload_clean.csv"
        df = pd.read_csv(file_path, encoding='latin-1')
        
        # Convert date columns
        if 'Date intervention' in df.columns:
            df['Date intervention'] = pd.to_datetime(df['Date intervention'], errors='coerce', dayfirst=True)
        
        # Clean numeric columns
        numeric_cols = ['Durée arrêt (h)', 'Nombre d\'heures MO', 'Coût total intervention']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load all datasets."""
        return self.load_amdec(), self.load_dispo(), self.load_workload()