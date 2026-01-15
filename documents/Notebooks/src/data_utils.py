"""
Data Utilities Module
====================
Functions for loading, saving, and handling CSV files with encoding detection.
"""

import pandas as pd
import numpy as np
import chardet
from pathlib import Path
from typing import Optional, Union, Dict, List
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


def detect_encoding(file_path: Union[str, Path], n_bytes: int = 100000) -> str:
    """
    Detect the encoding of a file using chardet.
    
    Parameters:
    -----------
    file_path : str or Path
        Path to the file
    n_bytes : int
        Number of bytes to read for detection (default: 100000)
    
    Returns:
    --------
    str : Detected encoding
    """
    file_path = Path(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(n_bytes)
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            
            logger.info(f"Detected encoding for {file_path.name}: {encoding} (confidence: {confidence:.2%})")
            return encoding
    except Exception as e:
        logger.error(f"Error detecting encoding for {file_path.name}: {e}")
        return 'utf-8'  # Fallback to utf-8


def load_csv(file_path: Union[str, Path], 
             encoding: Optional[str] = None,
             detect_enc: bool = True,
             **kwargs) -> pd.DataFrame:
    """
    Load a CSV file with automatic encoding detection.
    
    Parameters:
    -----------
    file_path : str or Path
        Path to the CSV file
    encoding : str, optional
        Specific encoding to use (if None, auto-detect)
    detect_enc : bool
        Whether to auto-detect encoding (default: True)
    **kwargs : additional arguments passed to pd.read_csv
    
    Returns:
    --------
    pd.DataFrame : Loaded dataframe
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Auto-detect encoding if not provided
    if encoding is None and detect_enc:
        encoding = detect_encoding(file_path)
    elif encoding is None:
        encoding = 'utf-8'
    
    try:
        logger.info(f"Loading {file_path.name} with encoding: {encoding}")
        # Try to detect decimal separator (comma vs period)
        df = pd.read_csv(file_path, encoding=encoding, **kwargs)
        
        # Convert numeric columns with comma as decimal separator
        df = _fix_numeric_columns(df)
        
        logger.success(f"Successfully loaded {file_path.name} - Shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading {file_path.name} with encoding {encoding}: {e}")
        
        # Try alternative encodings
        alternative_encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for alt_enc in alternative_encodings:
            if alt_enc != encoding:
                try:
                    logger.info(f"Trying alternative encoding: {alt_enc}")
                    df = pd.read_csv(file_path, encoding=alt_enc, **kwargs)
                    df = _fix_numeric_columns(df)
                    logger.success(f"Successfully loaded with {alt_enc} - Shape: {df.shape}")
                    return df
                except:
                    continue
        
        raise ValueError(f"Could not load {file_path.name} with any encoding")


def _fix_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix numeric columns that have comma as decimal separator.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    
    Returns:
    --------
    pd.DataFrame : Dataframe with fixed numeric columns
    """
    for col in df.columns:
        # Check if column is object type and might be numeric
        if df[col].dtype == 'object':
            # Try to convert, replacing comma with period
            try:
                # Check if it looks like a number with comma decimal
                sample = df[col].dropna().head(10).astype(str)
                if sample.str.contains(',').any() and not sample.str.contains('[a-zA-Z]', regex=True).any():
                    # Replace comma with period and convert to float
                    df[col] = df[col].astype(str).str.replace(',', '.').replace('nan', np.nan)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    logger.info(f"  Converted {col} from comma decimal to numeric")
            except:
                pass
    
    return df


def load_all_datasets(raw_data_dir: Union[str, Path], 
                     file_names: Optional[Dict[str, str]] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all GMAO datasets from the raw data directory.
    
    Parameters:
    -----------
    raw_data_dir : str or Path
        Directory containing raw CSV files
    file_names : dict, optional
        Dictionary mapping dataset names to file names
        Default: {'AMDEC': 'AMDEC_clean.csv', 'GMAO': 'GMAO_integrator_clean.csv', 
                  'Workload': 'Workload_clean.csv'}
    
    Returns:
    --------
    dict : Dictionary of dataframes {dataset_name: dataframe}
    """
    if file_names is None:
        file_names = {
            'AMDEC': 'AMDEC_clean.csv',
            'GMAO': 'GMAO_integrator_clean.csv',
            'Workload': 'Workload_clean.csv'
        }
    
    raw_data_dir = Path(raw_data_dir)
    datasets = {}
    
    logger.info(f"Loading datasets from {raw_data_dir}")
    
    for name, file_name in file_names.items():
        file_path = raw_data_dir / file_name
        try:
            datasets[name] = load_csv(file_path)
        except Exception as e:
            logger.warning(f"Could not load {name} dataset: {e}")
    
    logger.success(f"Loaded {len(datasets)} datasets")
    return datasets


def save_csv(df: pd.DataFrame, 
             file_path: Union[str, Path],
             encoding: str = 'utf-8',
             **kwargs) -> None:
    """
    Save a dataframe to CSV with specified encoding.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Dataframe to save
    file_path : str or Path
        Output file path
    encoding : str
        Encoding to use (default: 'utf-8')
    **kwargs : additional arguments passed to pd.to_csv
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        df.to_csv(file_path, encoding=encoding, index=False, **kwargs)
        logger.success(f"Saved {file_path.name} - Shape: {df.shape}")
    except Exception as e:
        logger.error(f"Error saving {file_path.name}: {e}")
        raise


def get_dataset_info(df: pd.DataFrame, dataset_name: str = "Dataset") -> pd.DataFrame:
    """
    Get comprehensive information about a dataset.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    dataset_name : str
        Name of the dataset for display
    
    Returns:
    --------
    pd.DataFrame : Summary information about the dataset
    """
    logger.info(f"Generating info for {dataset_name}")
    
    info_data = {
        'Column': df.columns,
        'Type': df.dtypes.values,
        'Non-Null Count': df.count().values,
        'Null Count': df.isnull().sum().values,
        'Null %': (df.isnull().sum() / len(df) * 100).round(2).values,
        'Unique Values': [df[col].nunique() for col in df.columns],
        'Sample Value': [df[col].dropna().iloc[0] if not df[col].dropna().empty else None 
                        for col in df.columns]
    }
    
    info_df = pd.DataFrame(info_data)
    return info_df


def display_dataset_summary(datasets: Dict[str, pd.DataFrame]) -> None:
    """
    Display summary statistics for multiple datasets.
    
    Parameters:
    -----------
    datasets : dict
        Dictionary of dataframes {name: dataframe}
    """
    logger.info("=" * 80)
    logger.info("DATASET SUMMARY")
    logger.info("=" * 80)
    
    for name, df in datasets.items():
        logger.info(f"\n{name} Dataset:")
        logger.info(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
        logger.info(f"  Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        logger.info(f"  Date range: {df.select_dtypes(include=['datetime64']).apply(lambda x: f'{x.min()} to {x.max()}').to_dict() if not df.select_dtypes(include=['datetime64']).empty else 'No dates parsed'}")