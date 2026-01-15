"""
data_finetune/test_setup.py

Test script to verify the installation and data loading.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from data_finetune.utils.data_loader import DataLoader
        from data_finetune.utils.formatters import AlpacaFormatter, ShareGPTFormatter, ChatMLFormatter
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_data_loading():
    """Test that data can be loaded."""
    print("\nTesting data loading...")
    try:
        from data_finetune.utils.data_loader import DataLoader
        
        loader = DataLoader("data/raw")
        amdec, dispo, workload = loader.load_all()
        
        print(f"✓ AMDEC loaded: {len(amdec)} rows")
        print(f"✓ Dispo loaded: {len(dispo)} rows")
        print(f"✓ Workload loaded: {len(workload)} rows")
        return True
    except Exception as e:
        print(f"✗ Data loading error: {e}")
        return False


def test_generator():
    """Test that generator can create samples."""
    print("\nTesting sample generation...")
    try:
        from data_finetune.generate_all_datasets import FinetuneDatasetGenerator
        
        generator = FinetuneDatasetGenerator()
        
        # Generate small test batch
        generator.generate_all(
            qa_samples=10,
            instruction_samples=5,
            classification_samples=5,
            summarization_samples=5,
            prediction_samples=5,
            diagnostic_samples=5,
            comparison_samples=5,
            timeseries_samples=5,
            multidoc_samples=5,
            conversation_samples=5,
            validation_samples=5,
            documentation_samples=5
        )
        
        total = sum(len(data) for data in generator.all_datasets.values())
        print(f"✓ Generated {total} test samples")
        return True
    except Exception as e:
        print(f"✗ Generation error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING DATA_FINETUNE SETUP")
    print("="*60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Data Loading", test_data_loading()))
    results.append(("Generator", test_generator()))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Setup is complete.")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
