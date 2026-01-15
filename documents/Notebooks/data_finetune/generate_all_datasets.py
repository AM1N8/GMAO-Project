"""
data_finetune/generate_all_datasets.py

Complete LLM fine-tuning data generator for GMAO datasets.
Generates all 12 types of training data for LLM fine-tuning.
"""

import pandas as pd
import numpy as np
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
import itertools
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Import custom generators
from .generators.qa_generator import QAGenerator
from .generators.instruction_generator import InstructionGenerator
from .generators.simple_generators import (
    ClassificationGenerator, 
    SummarizationGenerator, 
    PredictionGenerator
)
from .generators.advanced_generators import (
    DiagnosticGenerator,
    ComparisonGenerator,
    TimeSeriesGenerator,
    MultiDocGenerator,
    ConversationGenerator,
    ValidationGenerator,
    DocumentationGenerator
)
from .utils.data_loader import DataLoader
from .utils.formatters import AlpacaFormatter, ShareGPTFormatter, ChatMLFormatter


class FinetuneDatasetGenerator:
    """Master class to generate all fine-tuning datasets."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "data" / "raw"
        self.output_path = self.base_path / "data_finetune" / "outputs"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Load data
        print("Loading datasets...")
        self.loader = DataLoader(str(self.data_path))
        self.amdec_df, self.dispo_df, self.workload_df = self.loader.load_all()
        
        # Initialize generators
        print("Initializing generators...")
        self._init_generators()
        
        # Initialize formatters
        self.formatters = {
            'alpaca': AlpacaFormatter(),
            'sharegpt': ShareGPTFormatter(),
            'chatml': ChatMLFormatter()
        }
        
        self.all_datasets = {}
        
    def _init_generators(self):
        """Initialize all data generators."""
        self.qa_gen = QAGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.instruction_gen = InstructionGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.classification_gen = ClassificationGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.summarization_gen = SummarizationGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.prediction_gen = PredictionGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.diagnostic_gen = DiagnosticGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.comparison_gen = ComparisonGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.timeseries_gen = TimeSeriesGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.multidoc_gen = MultiDocGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.conversation_gen = ConversationGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.validation_gen = ValidationGenerator(self.amdec_df, self.dispo_df, self.workload_df)
        self.documentation_gen = DocumentationGenerator(self.amdec_df, self.dispo_df, self.workload_df)
    
    def generate_all(self, 
                     qa_samples: int = 3000,
                     instruction_samples: int = 800,
                     classification_samples: int = 500,
                     summarization_samples: int = 400,
                     prediction_samples: int = 400,
                     diagnostic_samples: int = 400,
                     comparison_samples: int = 300,
                     timeseries_samples: int = 300,
                     multidoc_samples: int = 500,
                     conversation_samples: int = 250,
                     validation_samples: int = 200,
                     documentation_samples: int = 150):
        """Generate all dataset types."""
        
        print("\n" + "="*80)
        print("STARTING COMPLETE DATASET GENERATION")
        print("="*80 + "\n")
        
        # 1. QA Pairs
        print("1. Generating Question-Answering pairs...")
        self.all_datasets['qa'] = self.qa_gen.generate_all(qa_samples)
        print(f"   ✓ Generated {len(self.all_datasets['qa'])} QA pairs\n")
        
        # 2. Instructions
        print("2. Generating Instruction-Following tasks...")
        self.all_datasets['instructions'] = self.instruction_gen.generate_all(instruction_samples)
        print(f"   ✓ Generated {len(self.all_datasets['instructions'])} instructions\n")
        
        # 3. Classifications
        print("3. Generating Classification tasks...")
        self.all_datasets['classifications'] = self.classification_gen.generate_all(classification_samples)
        print(f"   ✓ Generated {len(self.all_datasets['classifications'])} classifications\n")
        
        # 4. Summarizations
        print("4. Generating Summarization tasks...")
        self.all_datasets['summarizations'] = self.summarization_gen.generate_all(summarization_samples)
        print(f"   ✓ Generated {len(self.all_datasets['summarizations'])} summaries\n")
        
        # 5. Predictions
        print("5. Generating Predictive/Analytical tasks...")
        self.all_datasets['predictions'] = self.prediction_gen.generate_all(prediction_samples)
        print(f"   ✓ Generated {len(self.all_datasets['predictions'])} predictions\n")
        
        # 6. Diagnostics
        print("6. Generating Diagnostic Reasoning chains...")
        self.all_datasets['diagnostics'] = self.diagnostic_gen.generate_all(diagnostic_samples)
        print(f"   ✓ Generated {len(self.all_datasets['diagnostics'])} diagnostics\n")
        
        # 7. Comparisons
        print("7. Generating Comparison & Benchmarking tasks...")
        self.all_datasets['comparisons'] = self.comparison_gen.generate_all(comparison_samples)
        print(f"   ✓ Generated {len(self.all_datasets['comparisons'])} comparisons\n")
        
        # 8. Time Series
        print("8. Generating Time-Series Analysis tasks...")
        self.all_datasets['timeseries'] = self.timeseries_gen.generate_all(timeseries_samples)
        print(f"   ✓ Generated {len(self.all_datasets['timeseries'])} time-series analyses\n")
        
        # 9. Multi-Document
        print("9. Generating Multi-Document Reasoning tasks...")
        self.all_datasets['multidoc'] = self.multidoc_gen.generate_all(multidoc_samples)
        print(f"   ✓ Generated {len(self.all_datasets['multidoc'])} multi-doc tasks\n")
        
        # 10. Conversations
        print("10. Generating Conversational Context tasks...")
        self.all_datasets['conversations'] = self.conversation_gen.generate_all(conversation_samples)
        print(f"   ✓ Generated {len(self.all_datasets['conversations'])} conversations\n")
        
        # 11. Validations
        print("11. Generating Data Validation tasks...")
        self.all_datasets['validations'] = self.validation_gen.generate_all(validation_samples)
        print(f"   ✓ Generated {len(self.all_datasets['validations'])} validations\n")
        
        # 12. Documentation
        print("12. Generating Technical Documentation tasks...")
        self.all_datasets['documentations'] = self.documentation_gen.generate_all(documentation_samples)
        print(f"   ✓ Generated {len(self.all_datasets['documentations'])} documentations\n")
        
        return self.all_datasets
    
    def save_all_formats(self):
        """Save datasets in all formats (Alpaca, ShareGPT, ChatML)."""
        
        print("\n" + "="*80)
        print("SAVING DATASETS IN ALL FORMATS")
        print("="*80 + "\n")
        
        # Combine all datasets
        all_data = []
        for dataset_type, data in self.all_datasets.items():
            for item in data:
                item['dataset_type'] = dataset_type
                all_data.append(item)
        
        print(f"Total samples: {len(all_data)}")
        
        # Shuffle
        random.shuffle(all_data)
        
        # Save in each format
        for format_name, formatter in self.formatters.items():
            print(f"\nSaving {format_name.upper()} format...")
            
            # Format data
            formatted_data = formatter.format_batch(all_data)
            
            # Save individual dataset types
            for dataset_type in self.all_datasets.keys():
                type_data = [d for d in all_data if d['dataset_type'] == dataset_type]
                formatted_type = formatter.format_batch(type_data)
                
                output_file = self.output_path / f"{dataset_type}_{format_name}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(formatted_type, f, ensure_ascii=False, indent=2)
                print(f"   ✓ Saved {output_file.name} ({len(formatted_type)} samples)")
            
            # Save combined dataset
            combined_file = self.output_path / f"combined_all_{format_name}.json"
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=2)
            print(f"   ✓ Saved {combined_file.name} ({len(formatted_data)} samples)")
            
            # Save train/val/test splits (80/10/10)
            n = len(formatted_data)
            train_size = int(0.8 * n)
            val_size = int(0.1 * n)
            
            train_data = formatted_data[:train_size]
            val_data = formatted_data[train_size:train_size + val_size]
            test_data = formatted_data[train_size + val_size:]
            
            splits = {
                'train': train_data,
                'validation': val_data,
                'test': test_data
            }
            
            for split_name, split_data in splits.items():
                split_file = self.output_path / f"{split_name}_{format_name}.json"
                with open(split_file, 'w', encoding='utf-8') as f:
                    json.dump(split_data, f, ensure_ascii=False, indent=2)
                print(f"   ✓ Saved {split_file.name} ({len(split_data)} samples)")
    
    def generate_statistics(self):
        """Generate statistics about the datasets."""
        
        print("\n" + "="*80)
        print("DATASET STATISTICS")
        print("="*80 + "\n")
        
        stats = {
            'total_samples': 0,
            'by_type': {},
            'avg_input_length': 0,
            'avg_output_length': 0,
            'generation_date': datetime.now().isoformat()
        }
        
        all_inputs = []
        all_outputs = []
        
        for dataset_type, data in self.all_datasets.items():
            stats['by_type'][dataset_type] = len(data)
            stats['total_samples'] += len(data)
            
            for item in data:
                all_inputs.append(len(item['input']))
                all_outputs.append(len(item['output']))
        
        stats['avg_input_length'] = int(np.mean(all_inputs))
        stats['avg_output_length'] = int(np.mean(all_outputs))
        stats['max_input_length'] = max(all_inputs)
        stats['max_output_length'] = max(all_outputs)
        
        # Print statistics
        print(f"Total Samples: {stats['total_samples']:,}")
        print(f"\nBreakdown by Type:")
        for dtype, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            percentage = (count / stats['total_samples']) * 100
            print(f"  {dtype:20s}: {count:5,} ({percentage:5.1f}%)")
        
        print(f"\nText Statistics:")
        print(f"  Avg Input Length:  {stats['avg_input_length']:,} chars")
        print(f"  Avg Output Length: {stats['avg_output_length']:,} chars")
        print(f"  Max Input Length:  {stats['max_input_length']:,} chars")
        print(f"  Max Output Length: {stats['max_output_length']:,} chars")
        
        # Save statistics
        stats_file = self.output_path / "dataset_statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Statistics saved to {stats_file.name}")
        
        return stats


def main():
    """Main execution function."""
    
    print("\n" + "="*80)
    print(" LLM FINE-TUNING DATASET GENERATOR FOR GMAO")
    print("="*80 + "\n")
    
    # Initialize generator
    generator = FinetuneDatasetGenerator()
    
    # Generate all datasets
    generator.generate_all(
        qa_samples=3000,
        instruction_samples=800,
        classification_samples=500,
        summarization_samples=400,
        prediction_samples=400,
        diagnostic_samples=400,
        comparison_samples=300,
        timeseries_samples=300,
        multidoc_samples=500,
        conversation_samples=250,
        validation_samples=200,
        documentation_samples=150
    )
    
    # Save in all formats
    generator.save_all_formats()
    
    # Generate statistics
    generator.generate_statistics()
    
    print("\n" + "="*80)
    print("✓ COMPLETE! All datasets generated successfully.")
    print(f"✓ Output location: {generator.output_path}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()