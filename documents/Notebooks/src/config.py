"""
Configuration Module
===================
Central configuration for paths, constants, and parameters.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
CLEANED_DATA_DIR = OUTPUTS_DIR / "cleaned_data"

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, 
                  OUTPUTS_DIR, FIGURES_DIR, CLEANED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Data file names
AMDEC_FILE = "AMDEC_clean.csv"
GMAO_FILE = "GMAO_integrator_clean.csv"
WORKLOAD_FILE = "Workload_clean.csv"

# Column configurations
DATE_COLUMNS = {
    'AMDEC': ['Date intervention', 'Date demande'],
    'GMAO': ['Date intervention'],
    'Workload': ['Date intervention']
}

# Date format (adjust based on your data)
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# Analysis parameters
OUTLIER_THRESHOLD = 3  # Standard deviations for outlier detection
MISSING_THRESHOLD = 0.5  # Drop columns with >50% missing values

# Visualization settings
FIGURE_SIZE = (12, 6)
COLOR_PALETTE = "viridis"
DPI = 300

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"