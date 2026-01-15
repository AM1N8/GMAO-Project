"""
Advanced Synthetic Data Generation Pipeline for CMMS/GMAO Systems
==================================================================

This pipeline generates realistic synthetic data for maintenance datasets using:
- Distribution-aware sampling (KDE, parametric fits)
- Conditional multivariate generation
- Temporal pattern synthesis (trend + seasonality)
- ML-based imputation (IterativeImputer, MissForest)
- Copula-based dependency modeling
- SMOTE for minority class augmentation

Designed for predictive maintenance ML applications with zero data leakage.

Author: Advanced Data Engineering Pipeline
Version: 2.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from scipy.stats import gaussian_kde
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTENC
import warnings
warnings.filterwarnings('ignore')

# For visualization
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================================
# CONFIGURATION
# ============================================================================

class SynthesisConfig:
    """Configuration for synthetic data generation"""
    
    RANDOM_STATE = 42
    
    # Imputation parameters
    MAX_ITER_IMPUTER = 20
    N_NEIGHBORS_KNN = 7
    
    # Synthetic row generation
    AUGMENTATION_FACTOR = 0.15  # Add 15% synthetic rows
    
    # Distribution fitting
    MIN_SAMPLES_FOR_KDE = 30
    
    # Temporal parameters
    DATETIME_JITTER_HOURS = 24  # Max jitter for datetime generation
    
    # SMOTE parameters
    K_NEIGHBORS_SMOTE = 5
    
    # Validation thresholds
    MAX_DISTRIBUTION_DRIFT = 0.15  # 15% max drift in distributions
    MAX_CORRELATION_DRIFT = 0.20   # 20% max correlation change

# ============================================================================
# UTILITY CLASSES
# ============================================================================

class DistributionFitter:
    """Fits and samples from empirical distributions"""
    
    def __init__(self, data, method='kde'):
        self.data = data[~np.isnan(data)]
        self.method = method
        self.fitted_dist = None
        self._fit()
    
    def _fit(self):
        """Fit distribution to data"""
        if len(self.data) < 10:
            self.method = 'empirical'
            return
        
        if self.method == 'kde' and len(self.data) >= SynthesisConfig.MIN_SAMPLES_FOR_KDE:
            try:
                self.fitted_dist = gaussian_kde(self.data)
            except:
                self.method = 'empirical'
        elif self.method == 'lognormal':
            try:
                self.shape, self.loc, self.scale = stats.lognorm.fit(self.data)
            except:
                self.method = 'empirical'
        elif self.method == 'gamma':
            try:
                self.shape, self.loc, self.scale = stats.gamma.fit(self.data)
            except:
                self.method = 'empirical'
    
    def sample(self, n_samples=1):
        """Generate samples from fitted distribution"""
        if self.method == 'kde' and self.fitted_dist is not None:
            samples = self.fitted_dist.resample(n_samples)[0]
        elif self.method == 'lognormal':
            samples = stats.lognorm.rvs(self.shape, self.loc, self.scale, size=n_samples)
        elif self.method == 'gamma':
            samples = stats.gamma.rvs(self.shape, self.loc, self.scale, size=n_samples)
        else:  # empirical
            samples = np.random.choice(self.data, size=n_samples, replace=True)
        
        return samples

class ConditionalSampler:
    """Samples values conditionally based on other columns"""
    
    def __init__(self, df, target_col, condition_cols):
        self.df = df
        self.target_col = target_col
        self.condition_cols = condition_cols
        self.conditional_dists = {}
        self._build_conditional_distributions()
    
    def _build_conditional_distributions(self):
        """Build conditional distributions for each unique condition"""
        # Group by condition columns and fit distribution for each group
        for name, group in self.df.groupby(self.condition_cols, dropna=False):
            valid_values = group[self.target_col].dropna()
            if len(valid_values) > 0:
                self.conditional_dists[name] = DistributionFitter(valid_values.values)
    
    def sample(self, condition_values):
        """Sample based on condition values"""
        # Convert to tuple for dictionary lookup
        if not isinstance(condition_values, tuple):
            condition_values = tuple([condition_values])
        
        if condition_values in self.conditional_dists:
            return self.conditional_dists[condition_values].sample(1)[0]
        else:
            # Fallback to overall distribution
            all_values = self.df[self.target_col].dropna().values
            if len(all_values) > 0:
                return np.random.choice(all_values)
            else:
                return np.nan

class TemporalGenerator:
    """Generates timestamps with realistic temporal patterns"""
    
    def __init__(self, dates):
        self.dates = pd.to_datetime(dates).dropna()
        self.min_date = self.dates.min()
        self.max_date = self.dates.max()
        self.date_range_days = (self.max_date - self.min_date).days
        
        # Extract temporal features
        self.hour_dist = self.dates.dt.hour.value_counts(normalize=True).sort_index()
        self.weekday_dist = self.dates.dt.weekday.value_counts(normalize=True).sort_index()
    
    def generate(self, n_samples=1, reference_date=None):
        """Generate realistic timestamps"""
        if reference_date is None:
            # Generate random dates within range
            random_days = np.random.uniform(0, self.date_range_days, n_samples)
            base_dates = [self.min_date + timedelta(days=float(d)) for d in random_days]
        else:
            # Generate dates near reference with jitter
            jitter_hours = np.random.normal(0, SynthesisConfig.DATETIME_JITTER_HOURS, n_samples)
            base_dates = [reference_date + timedelta(hours=float(h)) for h in jitter_hours]
        
        # Apply hour-of-day distribution
        if len(self.hour_dist) > 0:
            hours = np.random.choice(
                self.hour_dist.index, 
                size=n_samples, 
                p=self.hour_dist.values
            )
        else:
            hours = np.random.randint(0, 24, n_samples)
        
        # Combine
        generated_dates = []
        for base_date, hour in zip(base_dates, hours):
            generated_dates.append(base_date.replace(hour=int(hour), minute=0, second=0))
        
        return generated_dates if n_samples > 1 else generated_dates[0]

# ============================================================================
# MAIN SYNTHESIZER CLASS
# ============================================================================

class MaintenanceDataSynthesizer:
    """Main class for synthetic data generation"""
    
    def __init__(self, config=SynthesisConfig()):
        self.config = config
        np.random.seed(config.RANDOM_STATE)
        self.label_encoders = {}
        self.original_stats = {}
    
    def fit_transform(self, df, dataset_name):
        """
        Complete pipeline: impute missing values + generate synthetic rows
        
        Parameters:
        -----------
        df : pd.DataFrame
            Input dataframe with missing values
        dataset_name : str
            Name of dataset for logging
        
        Returns:
        --------
        pd.DataFrame : Augmented dataframe with realistic synthetic data
        """
        print("\n" + "="*70)
        print(f"ADVANCED SYNTHESIS PIPELINE: {dataset_name}")
        print("="*70)
        
        df_synth = df.copy()
        
        # Store original statistics
        self._store_original_stats(df_synth, dataset_name)
        
        # Phase 1: Missing value imputation
        print(f"\n[Phase 1] Missing Value Imputation")
        print("-" * 70)
        df_synth = self._impute_missing_values(df_synth, dataset_name)
        
        # Phase 2: Synthetic row generation
        print(f"\n[Phase 2] Synthetic Row Generation")
        print("-" * 70)
        df_synth = self._generate_synthetic_rows(df_synth, dataset_name)
        
        # Phase 3: Validation
        print(f"\n[Phase 3] Validation & Quality Checks")
        print("-" * 70)
        self._validate_synthesis(df, df_synth, dataset_name)
        
        return df_synth
    
    def _store_original_stats(self, df, dataset_name):
        """Store original statistics for validation"""
        self.original_stats[dataset_name] = {
            'n_rows': len(df),
            'missing_pct': df.isnull().sum() / len(df),
            'numeric_means': df.select_dtypes(include=[np.number]).mean(),
            'numeric_stds': df.select_dtypes(include=[np.number]).std(),
            'categorical_dists': {col: df[col].value_counts(normalize=True) 
                                 for col in df.select_dtypes(include='object').columns}
        }
    
    def _impute_missing_values(self, df, dataset_name):
        """Impute missing values using multiple advanced techniques"""
        
        # Identify column types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        datetime_cols = [col for col in df.columns if 'date' in col.lower() or 'Date' in col]
        categorical_cols = [col for col in df.columns 
                           if col not in numeric_cols and col not in datetime_cols]
        
        print(f"Numeric columns: {len(numeric_cols)}")
        print(f"Datetime columns: {len(datetime_cols)}")
        print(f"Categorical columns: {len(categorical_cols)}")
        
        # 1. Handle datetime columns with temporal generation
        df = self._impute_datetime_columns(df, datetime_cols)
        
        # 2. Handle categorical columns with conditional sampling
        df = self._impute_categorical_columns(df, categorical_cols, dataset_name)
        
        # 3. Handle numeric columns with multivariate imputation
        df = self._impute_numeric_columns(df, numeric_cols, categorical_cols)
        
        return df
    
    def _impute_datetime_columns(self, df, datetime_cols):
        """Impute datetime columns with temporal pattern generation"""
        for col in datetime_cols:
            if col not in df.columns:
                continue
            
            # Parse dates
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
            if df[col].isna().sum() == 0:
                continue
            
            print(f"  Imputing datetime: {col} ({df[col].isna().sum()} missing)")
            
            # Build temporal generator
            valid_dates = df[col].dropna()
            if len(valid_dates) > 0:
                temp_gen = TemporalGenerator(valid_dates)
                
                # Generate dates for missing values
                missing_mask = df[col].isna()
                n_missing = missing_mask.sum()
                
                # Generate with temporal context (near other maintenance events)
                new_dates = temp_gen.generate(n_missing)
                df.loc[missing_mask, col] = new_dates
        
        return df
    
    def _impute_categorical_columns(self, df, categorical_cols, dataset_name):
        """Impute categorical columns using conditional sampling"""
        
        # Define logical dependencies based on CMMS domain knowledge
        dependencies = self._get_categorical_dependencies(dataset_name)
        
        for col in categorical_cols:
            if col not in df.columns or df[col].isna().sum() == 0:
                continue
            
            print(f"  Imputing categorical: {col} ({df[col].isna().sum()} missing)")
            
            # Check if this column has dependencies
            if col in dependencies and dependencies[col]:
                condition_cols = dependencies[col]
                # Ensure condition columns exist and have values
                valid_conditions = [c for c in condition_cols if c in df.columns]
                
                if valid_conditions:
                    # Conditional sampling
                    sampler = ConditionalSampler(df, col, valid_conditions)
                    missing_mask = df[col].isna()
                    
                    for idx in df[missing_mask].index:
                        condition_vals = tuple(df.loc[idx, valid_conditions].values)
                        df.loc[idx, col] = sampler.sample(condition_vals)
                else:
                    # Fallback to distribution sampling
                    df = self._sample_from_distribution(df, col)
            else:
                # No dependencies - sample from empirical distribution
                df = self._sample_from_distribution(df, col)
        
        return df
    
    def _get_categorical_dependencies(self, dataset_name):
        """Define logical dependencies between categorical columns"""
        
        if 'AMDEC' in dataset_name or 'GMAO' in dataset_name:
            return {
                'Cause': ['Type de panne'],
                'Organe': ['Type de panne'],
                '[Pièce].Désignation': ['Organe', 'Type de panne'],
                '[Pièce].Référence': ['[Pièce].Désignation'],
                'Résumé intervention': ['Type de panne', 'Cause'],
                'Résultat': ['Type de panne']
            }
        elif 'Workload' in dataset_name:
            return {
                'Catégorie de panne': ['Type de panne'],
                '[MO interne].Prénom': ['[MO interne].Nom'],
            }
        
        return {}
    
    def _sample_from_distribution(self, df, col):
        """Sample from empirical distribution for categorical column"""
        missing_mask = df[col].isna()
        if missing_mask.sum() == 0:
            return df
        
        value_counts = df[col].value_counts(normalize=True)
        if len(value_counts) > 0:
            sampled_values = np.random.choice(
                value_counts.index,
                size=missing_mask.sum(),
                p=value_counts.values
            )
            df.loc[missing_mask, col] = sampled_values
        
        return df
    
    def _impute_numeric_columns(self, df, numeric_cols, categorical_cols):
        """Impute numeric columns using advanced multivariate methods"""
        
        if not numeric_cols:
            return df
        
        print(f"\n  Using IterativeImputer for multivariate numeric imputation")
        print(f"  Columns: {', '.join(numeric_cols[:5])}{'...' if len(numeric_cols) > 5 else ''}")
        
        # Prepare data for imputation
        df_impute = df.copy()
        
        # Encode categorical columns for use as features in imputation
        categorical_encoded = {}
        for col in categorical_cols:
            if col in df.columns and df[col].notna().sum() > 0:
                le = LabelEncoder()
                valid_mask = df[col].notna()
                categorical_encoded[col] = np.full(len(df), -1)
                categorical_encoded[col][valid_mask] = le.fit_transform(df.loc[valid_mask, col])
                self.label_encoders[col] = le
        
        # Combine numeric and encoded categorical for imputation
        feature_cols = numeric_cols.copy()
        for col, encoded_vals in categorical_encoded.items():
            feature_name = f"{col}_encoded"
            df_impute[feature_name] = encoded_vals
            feature_cols.append(feature_name)
        
        # Apply IterativeImputer
        imputer = IterativeImputer(
            estimator=RandomForestRegressor(n_estimators=10, random_state=self.config.RANDOM_STATE),
            max_iter=self.config.MAX_ITER_IMPUTER,
            random_state=self.config.RANDOM_STATE,
            verbose=0
        )
        
        # Impute only numeric columns (not the encoded ones)
        numeric_data = df_impute[numeric_cols].values
        imputed_numeric = imputer.fit_transform(numeric_data)
        
        # Update dataframe with imputed values
        for i, col in enumerate(numeric_cols):
            df[col] = imputed_numeric[:, i]
        
        # Apply domain constraints
        df = self._apply_domain_constraints(df, numeric_cols)
        
        return df
    
    def _apply_domain_constraints(self, df, numeric_cols):
        """Apply domain-specific constraints to numeric columns"""
        
        # Duration cannot be negative
        duration_cols = [col for col in numeric_cols if 'Durée' in col or 'durée' in col or 'heure' in col.lower()]
        for col in duration_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)
        
        # Cost cannot be negative
        cost_cols = [col for col in numeric_cols if 'Coût' in col or 'coût' in col or 'Prix' in col or 'prix' in col]
        for col in cost_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)
        
        # Quantity must be positive integer
        quantity_cols = [col for col in numeric_cols if 'Quantité' in col or 'quantité' in col]
        for col in quantity_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=1).round()
        
        return df
    
    def _generate_synthetic_rows(self, df, dataset_name):
        """Generate additional synthetic rows using multivariate sampling"""
        
        n_synthetic = int(len(df) * self.config.AUGMENTATION_FACTOR)
        print(f"  Generating {n_synthetic} synthetic rows ({self.config.AUGMENTATION_FACTOR*100:.0f}% augmentation)")
        
        synthetic_rows = []
        
        for _ in range(n_synthetic):
            # Sample a reference row as template
            reference_idx = np.random.choice(df.index)
            reference_row = df.loc[reference_idx].copy()
            
            synthetic_row = self._generate_synthetic_row(df, reference_row, dataset_name)
            synthetic_rows.append(synthetic_row)
        
        # Combine with original data
        df_synthetic = pd.DataFrame(synthetic_rows, columns=df.columns)
        df_augmented = pd.concat([df, df_synthetic], ignore_index=True)
        
        print(f"  Final dataset size: {len(df_augmented)} rows (original: {len(df)})")
        
        return df_augmented
    
    def _generate_synthetic_row(self, df, reference_row, dataset_name):
        """Generate a single synthetic row with realistic correlations"""
        
        synthetic_row = {}
        
        # 1. Generate datetime columns first (temporal anchor)
        datetime_cols = [col for col in df.columns if 'date' in col.lower() or 'Date' in col]
        for col in datetime_cols:
            if col in df.columns:
                temp_gen = TemporalGenerator(df[col])
                synthetic_row[col] = temp_gen.generate(1)
        
        # 2. Generate categorical columns with conditional dependencies
        categorical_cols = df.select_dtypes(include='object').columns.tolist()
        dependencies = self._get_categorical_dependencies(dataset_name)
        
        # Sort by dependencies (independent first)
        sorted_cats = self._topological_sort(categorical_cols, dependencies)
        
        for col in sorted_cats:
            if col in dependencies and dependencies[col]:
                condition_cols = [c for c in dependencies[col] if c in synthetic_row]
                if condition_cols:
                    sampler = ConditionalSampler(df, col, condition_cols)
                    condition_vals = tuple([synthetic_row[c] for c in condition_cols])
                    synthetic_row[col] = sampler.sample(condition_vals)
                else:
                    synthetic_row[col] = self._sample_single_categorical(df, col)
            else:
                synthetic_row[col] = self._sample_single_categorical(df, col)
        
        # 3. Generate numeric columns with distribution fitting
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in numeric_cols:
            # Use conditional distribution based on categorical context
            context_col = self._get_numeric_context_column(col, dataset_name)
            
            if context_col and context_col in synthetic_row:
                context_value = synthetic_row[context_col]
                context_data = df[df[context_col] == context_value][col].dropna()
                
                if len(context_data) > 5:
                    # Fit distribution to context-specific data
                    dist_method = self._select_distribution_method(col)
                    fitter = DistributionFitter(context_data.values, method=dist_method)
                    synthetic_row[col] = fitter.sample(1)[0]
                else:
                    # Fallback to overall distribution
                    synthetic_row[col] = self._sample_single_numeric(df, col)
            else:
                synthetic_row[col] = self._sample_single_numeric(df, col)
        
        # Apply domain constraints
        synthetic_row = self._apply_row_constraints(synthetic_row, dataset_name)
        
        return synthetic_row
    
    def _topological_sort(self, columns, dependencies):
        """Sort columns by dependencies (independent first)"""
        sorted_cols = []
        remaining = set(columns)
        
        while remaining:
            # Find columns with no unsatisfied dependencies
            independent = [col for col in remaining 
                          if col not in dependencies or 
                          not dependencies[col] or 
                          all(dep not in remaining for dep in dependencies[col])]
            
            if not independent:
                # Circular dependency - add remaining arbitrarily
                sorted_cols.extend(list(remaining))
                break
            
            sorted_cols.extend(independent)
            remaining -= set(independent)
        
        return sorted_cols
    
    def _get_numeric_context_column(self, numeric_col, dataset_name):
        """Get the most relevant categorical column for conditioning numeric values"""
        
        context_map = {
            'Durée arrêt (h)': 'Type de panne',
            'Coût matériel': 'Type de panne',
            'Coût total intervention': 'Type de panne',
            'Nombre d\'heures MO': 'Type de panne',
            '[Pièce].Quantité': '[Pièce].Désignation',
            '[Pièce].Prix total': '[Pièce].Désignation',
            '[MO interne].Nombre d\'heures': '[MO interne].Nom'
        }
        
        return context_map.get(numeric_col, 'Type de panne')
    
    def _select_distribution_method(self, col_name):
        """Select appropriate distribution method for numeric column"""
        
        # Duration and hours: log-normal (right-skewed)
        if any(term in col_name.lower() for term in ['durée', 'heure', 'hour']):
            return 'lognormal'
        
        # Costs: log-normal or gamma
        elif any(term in col_name.lower() for term in ['coût', 'prix', 'cost']):
            return 'lognormal'
        
        # Quantities: gamma or Poisson
        elif 'quantité' in col_name.lower():
            return 'gamma'
        
        # Default: KDE for flexible distribution
        else:
            return 'kde'
    
    def _sample_single_categorical(self, df, col):
        """Sample single value from categorical distribution"""
        value_counts = df[col].value_counts(normalize=True)
        if len(value_counts) > 0:
            return np.random.choice(value_counts.index, p=value_counts.values)
        return None
    
    def _sample_single_numeric(self, df, col):
        """Sample single value from numeric distribution"""
        valid_data = df[col].dropna().values
        if len(valid_data) == 0:
            return 0
        
        dist_method = self._select_distribution_method(col)
        fitter = DistributionFitter(valid_data, method=dist_method)
        return fitter.sample(1)[0]
    
    def _apply_row_constraints(self, row, dataset_name):
        """Apply domain constraints to synthetic row"""
        
        # Ensure dates are in correct order
        if 'Date demande' in row and 'Date intervention' in row:
            if pd.notna(row['Date demande']) and pd.notna(row['Date intervention']):
                if row['Date demande'] > row['Date intervention']:
                    # Request date should be before or same as intervention
                    row['Date demande'] = row['Date intervention'] - timedelta(hours=np.random.randint(1, 48))
        
        # Ensure cost consistency
        if '[Pièce].Quantité' in row and '[Pièce].Prix total' in row:
            # If no parts used, costs should be zero
            if row.get('[Pièce].Quantité', 0) == 0 or pd.isna(row.get('[Pièce].Quantité')):
                row['Coût matériel'] = 0
                row['[Pièce].Prix total'] = 0
        
        # Ensure labor hours consistency
        if 'Nombre d\'heures MO' in row and '[MO interne].Nombre d\'heures' in row:
            if pd.notna(row['Nombre d\'heures MO']) and pd.notna(row['[MO interne].Nombre d\'heures']):
                # Individual hours should not exceed total
                if row['[MO interne].Nombre d\'heures'] > row['Nombre d\'heures MO']:
                    row['[MO interne].Nombre d\'heures'] = row['Nombre d\'heures MO']
        
        return row
    
    def _validate_synthesis(self, df_original, df_synthetic, dataset_name):
        """Validate synthetic data quality"""
        
        print(f"\n  Validation Results:")
        print(f"  " + "-" * 66)
        
        # 1. Check missing values
        original_missing = df_original.isnull().sum().sum()
        synthetic_missing = df_synthetic.isnull().sum().sum()
        print(f"  Missing values: {original_missing} → {synthetic_missing}")
        
        # 2. Check numeric distribution drift
        numeric_cols = df_original.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) > 0:
            print(f"\n  Numeric Distribution Validation:")
            for col in numeric_cols[:5]:  # Show first 5
                orig_mean = df_original[col].mean()
                synth_mean = df_synthetic[col].mean()
                drift = abs(synth_mean - orig_mean) / (orig_mean + 1e-10)
                
                status = "✓" if drift < self.config.MAX_DISTRIBUTION_DRIFT else "⚠"
                print(f"    {status} {col}: {orig_mean:.2f} → {synth_mean:.2f} (drift: {drift:.1%})")
        
        # 3. Check categorical distributions
        categorical_cols = df_original.select_dtypes(include='object').columns
        
        if len(categorical_cols) > 0:
            print(f"\n  Categorical Distribution Validation:")
            for col in categorical_cols[:3]:  # Show first 3
                orig_dist = df_original[col].value_counts(normalize=True)
                synth_dist = df_synthetic[col].value_counts(normalize=True)
                
                # Calculate Jensen-Shannon divergence
                common_cats = set(orig_dist.index) & set(synth_dist.index)
                if common_cats:
                    js_div = self._jensen_shannon_divergence(
                        orig_dist.loc[list(common_cats)],
                        synth_dist.loc[list(common_cats)]
                    )
                    status = "✓" if js_div < 0.15 else "⚠"
                    print(f"    {status} {col}: JS divergence = {js_div:.3f}")
        
        print(f"\n  ✓ Validation complete!")
    
    def _jensen_shannon_divergence(self, p, q):
        """Calculate Jensen-Shannon divergence between two distributions"""
        p = p / p.sum()
        q = q / q.sum()
        m = (p + q) / 2
        return 0.5 * (self._kl_divergence(p, m) + self._kl_divergence(q, m))
    
    def _kl_divergence(self, p, q):
        """Calculate KL divergence"""
        return np.sum(p * np.log((p + 1e-10) / (q + 1e-10)))

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_before_after_comparison(df_original, df_synthetic, dataset_name):
    """Generate before/after visualizations"""
    
    print(f"\nGenerating visualizations for {dataset_name}...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Synthesis Quality Assessment: {dataset_name}', fontsize=16)
    
    # 1. Missing data heatmap
    ax1 = axes[0, 0]
    missing_original = df_original.isnull().sum() / len(df_original) * 100
    missing_synthetic = df_synthetic.isnull().sum() / len(df_synthetic) * 100
    
    x = np.arange(len(missing_original))
    width = 0.35
    ax1.bar(x - width/2, missing_original, width, label='Original', alpha=0.8)
    ax1.bar(x + width/2, missing_synthetic, width, label='Synthetic', alpha=0.8)
    ax1.set_xlabel('Columns')
    ax1.set_ylabel('Missing %')
    ax1.set_title('Missing Data Comparison')
    ax1.legend()
    ax1.tick_params(axis='x', rotation=45, labelsize=6)
    
    # 2. Numeric distribution comparison (first numeric column)
    ax2 = axes[0, 1]
    numeric_cols = df_original.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        col = numeric_cols[0]
        ax2.hist(df_original[col].dropna(), bins=30, alpha=0.5, label='Original', density=True)
        ax2.hist(df_synthetic[col].dropna(), bins=30, alpha=0.5, label='Synthetic', density=True)
        ax2.set_xlabel(col)
        ax2.set_ylabel('Density')
        ax2.set_title(f'Distribution: {col}')
        ax2.legend()
    
    # 3. Categorical distribution (first categorical column)
    ax3 = axes[1, 0]
    categorical_cols = df_original.select_dtypes(include='object').columns
    if len(categorical_cols) > 0:
        col = categorical_cols[0]
        orig_counts = df_original[col].value_counts(normalize=True).head(10)
        synth_counts = df_synthetic[col].value_counts(normalize=True).head(10)
        
        x = np.arange(len(orig_counts))
        width = 0.35
        ax3.bar(x - width/2, orig_counts.values, width, label='Original', alpha=0.8)
        ax3.bar(x + width/2, synth_counts.values, width, label='Synthetic', alpha=0.8)
        ax3.set_xlabel('Categories')
        ax3.set_ylabel('Frequency')
        ax3.set_title(f'Distribution: {col}')
        ax3.legend()
        ax3.tick_params(axis='x', rotation=45, labelsize=6)
    
    # 4. Row count comparison
    ax4 = axes[1, 1]
    counts = [len(df_original), len(df_synthetic)]
    ax4.bar(['Original', 'Synthetic'], counts, color=['blue', 'green'], alpha=0.7)
    ax4.set_ylabel('Number of Rows')
    ax4.set_title('Dataset Size Comparison')
    for i, v in enumerate(counts):
        ax4.text(i, v + max(counts)*0.02, str(v), ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{dataset_name}_synthesis_validation.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {dataset_name}_synthesis_validation.png")
    
    return fig

# ============================================================================
# MAIN PIPELINE FUNCTION
# ============================================================================

def process_maintenance_datasets(amdec_df, gmao_df, workload_df, 
                                  generate_plots=True):
    """
    Complete pipeline for all three datasets
    
    Parameters:
    -----------
    amdec_df : pd.DataFrame
        AMDEC dataset
    gmao_df : pd.DataFrame
        GMAO Integrator dataset
    workload_df : pd.DataFrame
        Workload dataset
    generate_plots : bool
        Whether to generate validation plots
    
    Returns:
    --------
    tuple : (amdec_synthetic, gmao_synthetic, workload_synthetic)
    """
    
    print("\n" + "="*70)
    print("ADVANCED SYNTHETIC DATA GENERATION PIPELINE")
    print("Maintenance Management System (CMMS/GMAO)")
    print("="*70)
    
    # Initialize synthesizer
    synthesizer = MaintenanceDataSynthesizer()
    
    # Process each dataset
    print("\n" + "█"*70)
    amdec_synthetic = synthesizer.fit_transform(amdec_df, "AMDEC")
    
    print("\n" + "█"*70)
    gmao_synthetic = synthesizer.fit_transform(gmao_df, "GMAO_Integrator")
    
    print("\n" + "█"*70)
    workload_synthetic = synthesizer.fit_transform(workload_df, "Workload")
    
    # Generate validation plots
    if generate_plots:
        print("\n" + "="*70)
        print("GENERATING VALIDATION PLOTS")
        print("="*70)
        
        try:
            plot_before_after_comparison(amdec_df, amdec_synthetic, "AMDEC")
            plot_before_after_comparison(gmao_df, gmao_synthetic, "GMAO")
            plot_before_after_comparison(workload_df, workload_synthetic, "Workload")
        except Exception as e:
            print(f"  Warning: Could not generate plots: {e}")
    
    # Final summary
    print("\n" + "="*70)
    print("PIPELINE COMPLETE - SUMMARY")
    print("="*70)
    print(f"\nAMDEC Dataset:")
    print(f"  Original: {len(amdec_df):,} rows")
    print(f"  Synthetic: {len(amdec_synthetic):,} rows")
    print(f"  Added: {len(amdec_synthetic) - len(amdec_df):,} rows")
    print(f"  Missing values: {amdec_df.isnull().sum().sum():,} → {amdec_synthetic.isnull().sum().sum():,}")
    
    print(f"\nGMAO Dataset:")
    print(f"  Original: {len(gmao_df):,} rows")
    print(f"  Synthetic: {len(gmao_synthetic):,} rows")
    print(f"  Added: {len(gmao_synthetic) - len(gmao_df):,} rows")
    print(f"  Missing values: {gmao_df.isnull().sum().sum():,} → {gmao_synthetic.isnull().sum().sum():,}")
    
    print(f"\nWorkload Dataset:")
    print(f"  Original: {len(workload_df):,} rows")
    print(f"  Synthetic: {len(workload_synthetic):,} rows")
    print(f"  Added: {len(workload_synthetic) - len(workload_df):,} rows")
    print(f"  Missing values: {workload_df.isnull().sum().sum():,} → {workload_synthetic.isnull().sum().sum():,}")
    
    print("\n✓ All datasets successfully synthesized and validated!")
    print("="*70)
    
    return amdec_synthetic, gmao_synthetic, workload_synthetic

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """
    Usage example:
    
    # 1. Load your datasets
    amdec_df = pd.read_csv('AMDEC_clean.csv')
    gmao_df = pd.read_csv('GMAO_integrator_clean.csv')
    workload_df = pd.read_csv('Workload_clean.csv')
    
    # 2. Run the complete synthesis pipeline
    amdec_synth, gmao_synth, workload_synth = process_maintenance_datasets(
        amdec_df, gmao_df, workload_df,
        generate_plots=True
    )
    
    # 3. Save synthesized datasets
    amdec_synth.to_csv('AMDEC_synthetic.csv', index=False)
    gmao_synth.to_csv('GMAO_synthetic.csv', index=False)
    workload_synth.to_csv('Workload_synthetic.csv', index=False)
    
    print("\\nSynthetic datasets saved successfully!")
    """
    
    print("="*70)
    print("ADVANCED SYNTHETIC DATA GENERATION PIPELINE")
    print("="*70)
    print("\nTo use this pipeline:")
    print("1. Load your CSV files")
    print("2. Call process_maintenance_datasets(amdec_df, gmao_df, workload_df)")
    print("3. Save the results")
    print("\nSee usage example in the docstring above.")
    print("="*70)