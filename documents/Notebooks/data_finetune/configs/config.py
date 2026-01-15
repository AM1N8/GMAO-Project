"""
data_finetune/configs/config.py

Configuration for dataset generation.
"""

# Sample sizes for each dataset type
SAMPLE_SIZES = {
    'qa': 3000,
    'instructions': 800,
    'classifications': 500,
    'summarizations': 400,
    'predictions': 400,
    'diagnostics': 400,
    'comparisons': 300,
    'timeseries': 300,
    'multidoc': 500,
    'conversations': 250,
    'validations': 200,
    'documentations': 150
}

# Output formats to generate
OUTPUT_FORMATS = ['alpaca', 'sharegpt', 'chatml']

# Train/validation/test split ratios
SPLIT_RATIOS = {
    'train': 0.8,
    'validation': 0.1,
    'test': 0.1
}

# Data paths
DATA_PATHS = {
    'amdec': 'data/raw/GMAO_integrator_clean.csv',
    'dispo': 'data/raw/AMDEC_clean.csv',
    'workload': 'data/raw/Workload_clean.csv'
}

# Output directory
OUTPUT_DIR = 'data_finetune/outputs'

# Quality filters
QUALITY_FILTERS = {
    'min_output_length': 20,
    'max_output_length': 2000,
    'min_input_length': 5,
    'max_input_length': 1000
}

# Augmentation settings
AUGMENTATION = {
    'enabled': True,
    'paraphrase_ratio': 0.1,
    'synonym_replacement': False
}
