"""
GMAO Data Analysis Package
==========================
A modular package for preprocessing and analyzing maintenance data.

Modules:
--------
- config: Configuration and constants
- data_utils: Data loading and saving utilities
- preprocessing: Data cleaning and preprocessing functions
- eda_utils: Exploratory data analysis and visualization functions

Usage:
------
    from src.config import *
    from src.data_utils import load_csv, load_all_datasets
    from src.preprocessing import parse_dates, handle_missing_values
    from src.eda_utils import plot_distributions, plot_correlation_matrix
"""

__version__ = "1.0.0"
__author__ = "GMAO Analysis Team"
__all__ = [
    'config',
    'data_utils',
    'preprocessing',
    'eda_utils',
    'preprocess'
]