"""
data_finetune/examples/example_usage.py

Example script showing different ways to use the dataset generator.
"""

from data_finetune.generate_all_datasets import FinetuneDatasetGenerator

# Example 1: Generate all datasets with default settings
def example_default():
    print("Example 1: Default generation")
    generator = FinetuneDatasetGenerator()
    generator.generate_all()
    generator.save_all_formats()
    generator.generate_statistics()


# Example 2: Generate only specific dataset types
def example_custom():
    print("Example 2: Custom dataset sizes")
    generator = FinetuneDatasetGenerator()
    
    generator.generate_all(
        qa_samples=5000,  # More QA pairs
        instruction_samples=1000,  # More instructions
        conversation_samples=500,  # More conversations
        # Fewer of other types
        classification_samples=200,
        summarization_samples=200
    )
    
    generator.save_all_formats()


# Example 3: Generate only one format
def example_single_format():
    print("Example 3: Generate only Alpaca format")
    from data_finetune.utils.formatters import AlpacaFormatter
    
    generator = FinetuneDatasetGenerator()
    generator.generate_all(qa_samples=1000)
    
    # Save only Alpaca format
    formatter = AlpacaFormatter()
    all_data = []
    for dataset_type, data in generator.all_datasets.items():
        all_data.extend(data)
    
    formatted = formatter.format_batch(all_data)
    
    import json
    with open('data_finetune/outputs/custom_alpaca.json', 'w', encoding='utf-8') as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)


# Example 4: Filter by quality metrics
def example_quality_filter():
    print("Example 4: Quality filtering")
    generator = FinetuneDatasetGenerator()
    generator.generate_all()
    
    # Filter for high-quality samples
    quality_data = []
    for dataset_type, data in generator.all_datasets.items():
        for item in data:
            # Filter criteria
            if (len(item['output']) > 50 and 
                len(item['output']) < 1500 and
                len(item['input']) > 10):
                quality_data.append(item)
    
    print(f"High quality samples: {len(quality_data)}")


if __name__ == "__main__":
    # Run the example you want
    example_default()
