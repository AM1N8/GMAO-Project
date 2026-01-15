"""
EDA Utilities Module
===================
Functions for exploratory data analysis, visualizations, and statistical summaries.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Optional, Tuple, Dict
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Set default style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


def plot_missing_values(df: pd.DataFrame, 
                       title: str = "Missing Values Analysis",
                       figsize: Tuple[int, int] = (12, 6),
                       save_path: Optional[str] = None) -> None:
    """
    Visualize missing values in the dataframe.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    title : str
        Plot title
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    """
    logger.info("Generating missing values plot")
    
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    
    if len(missing) == 0:
        logger.info("No missing values to plot")
        return
    
    missing_pct = (missing / len(df) * 100).round(2)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # Bar plot of missing counts
    missing.plot(kind='barh', ax=ax1, color='coral')
    ax1.set_xlabel('Number of Missing Values')
    ax1.set_title('Missing Value Counts')
    ax1.grid(axis='x', alpha=0.3)
    
    # Bar plot of missing percentages
    missing_pct.plot(kind='barh', ax=ax2, color='steelblue')
    ax2.set_xlabel('Percentage (%)')
    ax2.set_title('Missing Value Percentages')
    ax2.grid(axis='x', alpha=0.3)
    
    plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()


def plot_distributions(df: pd.DataFrame,
                      columns: Optional[List[str]] = None,
                      ncols: int = 3,
                      figsize: Tuple[int, int] = (15, 10),
                      save_path: Optional[str] = None) -> None:
    """
    Plot distributions of numeric columns.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to plot (default: all numeric)
    ncols : int
        Number of columns in subplot grid
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    """
    logger.info("Generating distribution plots")
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(columns) == 0:
        logger.warning("No numeric columns to plot")
        return
    
    nrows = int(np.ceil(len(columns) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = axes.flatten() if nrows > 1 or ncols > 1 else [axes]
    
    for idx, col in enumerate(columns):
        ax = axes[idx]
        
        # Remove outliers for better visualization
        data = df[col].dropna()
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        filtered_data = data[(data >= Q1 - 1.5*IQR) & (data <= Q3 + 1.5*IQR)]
        
        # Plot histogram
        ax.hist(filtered_data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax2 = ax.twinx()
        
        # --- CORRECTED: Check for zero variance before attempting KDE plot ---
        if filtered_data.std() > 0:
            filtered_data.plot(kind='kde', ax=ax2, color='red', linewidth=2)
            ax2.set_ylabel('')
            ax2.set_yticks([])
        else:
            logger.warning(f"Skipping KDE plot for {col}: Data is constant (std is 0).")
        # ------------------------------------------------------------------
        
        ax.set_title(f'{col}\n(n={len(data):,}, μ={data.mean():.2f}, σ={data.std():.2f})')
        ax.set_xlabel('')
        ax.grid(axis='y', alpha=0.3)
    
    # Hide unused subplots
    for idx in range(len(columns), len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle('Distribution of Numeric Variables', fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()


def plot_correlation_matrix(df: pd.DataFrame,
                           columns: Optional[List[str]] = None,
                           method: str = 'pearson',
                           figsize: Tuple[int, int] = (12, 10),
                           save_path: Optional[str] = None) -> pd.DataFrame:
    """
    Plot correlation matrix heatmap.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to include (default: all numeric)
    method : str
        Correlation method ('pearson', 'spearman', 'kendall')
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    
    Returns:
    --------
    pd.DataFrame : Correlation matrix
    """
    logger.info(f"Generating correlation matrix ({method})")
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(columns) < 2:
        logger.warning("Need at least 2 numeric columns for correlation")
        return None
    
    # Calculate correlation
    corr = df[columns].corr(method=method)
    
    # Create mask for upper triangle
    mask = np.triu(np.ones_like(corr, dtype=bool))
    
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='coolwarm', 
                center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                vmin=-1, vmax=1, ax=ax)
    
    ax.set_title(f'Correlation Matrix ({method.capitalize()})', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()
    
    return corr


def plot_categorical_counts(df: pd.DataFrame,
                           columns: Optional[List[str]] = None,
                           top_n: int = 10,
                           ncols: int = 2,
                           figsize: Tuple[int, int] = (15, 10),
                           save_path: Optional[str] = None) -> None:
    """
    Plot value counts for categorical columns.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to plot (default: all categorical)
    top_n : int
        Number of top categories to show
    ncols : int
        Number of columns in subplot grid
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    """
    logger.info("Generating categorical counts plots")
    
    if columns is None:
        columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if len(columns) == 0:
        logger.warning("No categorical columns to plot")
        return
    
    nrows = int(np.ceil(len(columns) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = axes.flatten() if nrows > 1 or ncols > 1 else [axes]
    
    for idx, col in enumerate(columns):
        ax = axes[idx]
        
        # Get top N categories
        value_counts = df[col].value_counts().head(top_n)
        
        # Plot horizontal bar chart
        value_counts.plot(kind='barh', ax=ax, color='teal')
        ax.set_title(f'{col}\n(Total unique: {df[col].nunique()})')
        ax.set_xlabel('Count')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, v in enumerate(value_counts.values):
            ax.text(v, i, f' {v:,}', va='center')
    
    # Hide unused subplots
    for idx in range(len(columns), len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle('Categorical Variable Counts', fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()


def plot_time_series(df: pd.DataFrame,
                    date_column: str,
                    value_column: str,
                    agg_func: str = 'count',
                    freq: str = 'M',
                    figsize: Tuple[int, int] = (14, 6),
                    save_path: Optional[str] = None) -> pd.DataFrame:
    """
    Plot time series data.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    date_column : str
        Name of the date column
    value_column : str
        Name of the value column to aggregate
    agg_func : str
        Aggregation function ('count', 'sum', 'mean', 'median')
    freq : str
        Frequency for resampling ('D', 'W', 'M', 'Q', 'Y')
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    
    Returns:
    --------
    pd.DataFrame : Aggregated time series data
    """
    logger.info(f"Generating time series plot for {value_column}")
    
    if date_column not in df.columns:
        logger.error(f"Date column '{date_column}' not found")
        return None
    
    if value_column not in df.columns:
        logger.error(f"Value column '{value_column}' not found")
        return None
    
    # Prepare data
    ts_df = df[[date_column, value_column]].copy()
    ts_df = ts_df.set_index(date_column)
    
    # Resample and aggregate
    if agg_func == 'count':
        ts_data = ts_df.resample(freq).count()
    elif agg_func == 'sum':
        ts_data = ts_df.resample(freq).sum()
    elif agg_func == 'mean':
        ts_data = ts_df.resample(freq).mean()
    elif agg_func == 'median':
        ts_data = ts_df.resample(freq).median()
    else:
        raise ValueError(f"Unknown aggregation function: {agg_func}")
    
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(ts_data.index, ts_data[value_column], marker='o', linewidth=2, markersize=6)
    ax.fill_between(ts_data.index, ts_data[value_column], alpha=0.3)
    
    ax.set_title(f'{value_column} Over Time ({agg_func.capitalize()}, Freq: {freq})',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel(f'{value_column} ({agg_func})')
    ax.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()
    
    return ts_data


def generate_summary_statistics(df: pd.DataFrame,
                                columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Generate comprehensive summary statistics.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to summarize (default: all numeric)
    
    Returns:
    --------
    pd.DataFrame : Summary statistics
    """
    logger.info("Generating summary statistics")
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(columns) == 0:
        logger.warning("No numeric columns to summarize")
        return None
    
    summary = df[columns].describe().T
    
    # Add additional statistics
    summary['variance'] = df[columns].var()
    summary['skewness'] = df[columns].skew()
    summary['kurtosis'] = df[columns].kurtosis()
    summary['missing'] = df[columns].isnull().sum()
    summary['missing_%'] = (df[columns].isnull().sum() / len(df) * 100).round(2)
    
    return summary


def plot_boxplots(df: pd.DataFrame,
                 columns: Optional[List[str]] = None,
                 ncols: int = 3,
                 figsize: Tuple[int, int] = (15, 10),
                 save_path: Optional[str] = None) -> None:
    """
    Plot boxplots for numeric columns.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    columns : list, optional
        Columns to plot (default: all numeric)
    ncols : int
        Number of columns in subplot grid
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the figure
    """
    logger.info("Generating boxplots")
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(columns) == 0:
        logger.warning("No numeric columns to plot")
        return
    
    nrows = int(np.ceil(len(columns) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = axes.flatten() if nrows > 1 or ncols > 1 else [axes]
    
    for idx, col in enumerate(columns):
        ax = axes[idx]
        
        # Plot boxplot
        df.boxplot(column=col, ax=ax, grid=False)
        ax.set_title(col)
        ax.set_xlabel('')
    
    # Hide unused subplots
    for idx in range(len(columns), len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle('Boxplots - Outlier Detection', fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.success(f"Saved plot to {save_path}")
    
    plt.show()