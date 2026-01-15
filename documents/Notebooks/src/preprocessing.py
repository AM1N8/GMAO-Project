"""
Preprocessing Module
===================
Functions for data cleaning, missing value handling, encoding, and normalization.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Union, Tuple, Dict
from loguru import logger
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


def parse_dates(df: pd.DataFrame, 
                date_columns: List[str],
                date_format: Optional[str] = None,
                dayfirst: bool = True,
                errors: str = 'coerce') -> pd.DataFrame:
    """
    Parse date columns to datetime format.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    date_columns : list
        List of column names to parse as dates
    date_format : str, optional
        Specific date format (e.g., '%d/%m/%Y')
    dayfirst : bool
        Whether day comes first in ambiguous dates
    errors : str
        How to handle parsing errors ('coerce', 'raise', 'ignore')
    
    Returns:
    --------
    pd.DataFrame : Dataframe with parsed date columns
    """
    df = df.copy()
    
    for col in date_columns:
        if col in df.columns:
            try:
                logger.info(f"Parsing date column: {col}")
                if date_format:
                    df[col] = pd.to_datetime(df[col], format=date_format, errors=errors)
                else:
                    df[col] = pd.to_datetime(df[col], dayfirst=dayfirst, errors=errors)
                
                parsed_count = df[col].notna().sum()
                logger.success(f"  Parsed {parsed_count:,} dates in {col}")
            except Exception as e:
                logger.error(f"  Error parsing {col}: {e}")
        else:
            logger.warning(f"  Column {col} not found in dataframe")
    
    return df


def handle_missing_values(df: pd.DataFrame,
                         strategy: str = 'drop',
                         threshold: float = 0.5,
                         fill_value: Optional[Union[str, int, float]] = None,
                         columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Handle missing values in the dataframe.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    strategy : str
        Strategy to handle missing values:
        - 'drop': Drop rows/columns with missing values
        - 'fill': Fill missing values
        - 'median': Fill with median (numeric only)
        - 'mean': Fill with mean (numeric only)
        - 'mode': Fill with mode
    threshold : float
        For 'drop' strategy, drop columns with missing % > threshold
    fill_value : any
        Value to use for 'fill' strategy
    columns : list, optional
        Specific columns to apply strategy to
    
    Returns:
    --------
    pd.DataFrame : Dataframe with handled missing values
    """
    df = df.copy()
    initial_shape = df.shape
    
    logger.info(f"Handling missing values - Strategy: {strategy}")
    
    target_columns = columns if columns else df.columns
    
    if strategy == 'drop':
        # Drop columns with high missing percentage
        missing_pct = df[target_columns].isnull().sum() / len(df)
        cols_to_drop = missing_pct[missing_pct > threshold].index.tolist()
        
        if cols_to_drop:
            logger.info(f"  Dropping {len(cols_to_drop)} columns with >{threshold:.0%} missing: {cols_to_drop}")
            df = df.drop(columns=cols_to_drop)
        
        # Drop rows with any remaining missing values
        df = df.dropna(subset=[col for col in target_columns if col in df.columns])
        
    elif strategy == 'fill':
        if fill_value is None:
            fill_value = 0
        df[target_columns] = df[target_columns].fillna(fill_value)
        logger.info(f"  Filled missing values with: {fill_value}")
        
    elif strategy == 'median':
        numeric_cols = df[target_columns].select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
        logger.info(f"  Filled {len(numeric_cols)} numeric columns with median")
        
    elif strategy == 'mean':
        numeric_cols = df[target_columns].select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            mean_val = df[col].mean()
            df[col] = df[col].fillna(mean_val)
        logger.info(f"  Filled {len(numeric_cols)} numeric columns with mean")
        
    elif strategy == 'mode':
        for col in target_columns:
            if col in df.columns:
                mode_val = df[col].mode()[0] if not df[col].mode().empty else None
                if mode_val is not None:
                    df[col] = df[col].fillna(mode_val)
        logger.info(f"  Filled columns with mode")
    
    final_shape = df.shape
    logger.success(f"  Shape: {initial_shape} → {final_shape} (Removed {initial_shape[0] - final_shape[0]:,} rows, {initial_shape[1] - final_shape[1]} columns)")
    
    return df


def remove_duplicates(df: pd.DataFrame, 
                     subset: Optional[List[str]] = None,
                     keep: str = 'first') -> pd.DataFrame:
    """
    Remove duplicate rows from dataframe.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    subset : list, optional
        Column names to consider for identifying duplicates
    keep : str
        Which duplicate to keep ('first', 'last', False)
    
    Returns:
    --------
    pd.DataFrame : Dataframe without duplicates
    """
    df = df.copy()
    initial_rows = len(df)
    
    df = df.drop_duplicates(subset=subset, keep=keep)
    
    removed = initial_rows - len(df)
    if removed > 0:
        logger.info(f"Removed {removed:,} duplicate rows")
    else:
        logger.info("No duplicates found")
    
    return df


def detect_outliers(df: pd.DataFrame,
                   columns: Optional[List[str]] = None,
                   method: str = 'zscore',
                   threshold: float = 3.0) -> pd.DataFrame:
    """
    Detect outliers in numeric columns.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Numeric columns to check (default: all numeric)
    method : str
        Method for outlier detection:
        - 'zscore': Z-score method
        - 'iqr': Interquartile range method
    threshold : float
        Threshold for outlier detection (Z-score or IQR multiplier)
    
    Returns:
    --------
    pd.DataFrame : Boolean dataframe indicating outliers
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    outliers = pd.DataFrame(False, index=df.index, columns=columns)
    
    logger.info(f"Detecting outliers using {method} method")
    
    for col in columns:
        if col not in df.columns:
            continue
            
        if method == 'zscore':
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            outliers[col] = z_scores > threshold
            
        elif method == 'iqr':
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers[col] = (df[col] < (Q1 - threshold * IQR)) | (df[col] > (Q3 + threshold * IQR))
        
        outlier_count = outliers[col].sum()
        if outlier_count > 0:
            logger.info(f"  {col}: {outlier_count:,} outliers detected ({outlier_count/len(df)*100:.2f}%)")
    
    return outliers


def remove_outliers(df: pd.DataFrame,
                   columns: Optional[List[str]] = None,
                   method: str = 'zscore',
                   threshold: float = 3.0) -> pd.DataFrame:
    """
    Remove outliers from dataframe.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Numeric columns to check
    method : str
        Method for outlier detection ('zscore', 'iqr')
    threshold : float
        Threshold for outlier detection
    
    Returns:
    --------
    pd.DataFrame : Dataframe without outliers
    """
    df = df.copy()
    initial_rows = len(df)
    
    outliers = detect_outliers(df, columns, method, threshold)
    
    # Remove rows with any outlier
    mask = ~outliers.any(axis=1)
    df = df[mask]
    
    removed = initial_rows - len(df)
    logger.success(f"Removed {removed:,} rows with outliers")
    
    return df


def encode_categorical(df: pd.DataFrame,
                      columns: Optional[List[str]] = None,
                      method: str = 'label') -> Tuple[pd.DataFrame, Dict]:
    """
    Encode categorical variables.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to encode (default: all object/category columns)
    method : str
        Encoding method:
        - 'label': Label encoding
        - 'onehot': One-hot encoding
    
    Returns:
    --------
    tuple : (encoded_dataframe, encoders_dict)
    """
    df = df.copy()
    
    if columns is None:
        columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    encoders = {}
    
    logger.info(f"Encoding {len(columns)} categorical columns using {method} method")
    
    if method == 'label':
        for col in columns:
            if col in df.columns:
                le = LabelEncoder()
                # Handle NaN values
                mask = df[col].notna()
                df.loc[mask, col] = le.fit_transform(df.loc[mask, col].astype(str))
                encoders[col] = le
                logger.info(f"  {col}: {len(le.classes_)} unique categories")
                
    elif method == 'onehot':
        df = pd.get_dummies(df, columns=columns, prefix=columns, drop_first=True)
        logger.info(f"  Created {len(df.columns) - len(columns)} new columns")
    
    return df, encoders


def normalize_data(df: pd.DataFrame,
                  columns: Optional[List[str]] = None,
                  method: str = 'standard') -> Tuple[pd.DataFrame, object]:
    """
    Normalize/scale numeric data.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to normalize (default: all numeric)
    method : str
        Normalization method:
        - 'standard': StandardScaler (mean=0, std=1)
        - 'minmax': MinMaxScaler (range 0-1)
    
    Returns:
    --------
    tuple : (normalized_dataframe, scaler_object)
    """
    df = df.copy()
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    logger.info(f"Normalizing {len(columns)} numeric columns using {method} method")
    
    if method == 'standard':
        scaler = StandardScaler()
    elif method == 'minmax':
        scaler = MinMaxScaler()
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    df[columns] = scaler.fit_transform(df[columns])
    
    logger.success(f"  Normalized columns: {columns}")
    
    return df, scaler


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names by removing special characters and standardizing format.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    
    Returns:
    --------
    pd.DataFrame : Dataframe with cleaned column names
    """
    df = df.copy()
    
    # Remove leading/trailing whitespace
    df.columns = df.columns.str.strip()
    
    # Replace special characters with underscore
    # df.columns = df.columns.str.replace(r'[^\w\s]', '_', regex=True)
    
    # Replace multiple spaces/underscores with single underscore
    # df.columns = df.columns.str.replace(r'[\s_]+', '_', regex=True)
    
    logger.info("Column names cleaned")
    
    return df