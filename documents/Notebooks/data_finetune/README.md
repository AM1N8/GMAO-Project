# LLM Fine-tuning Dataset Generator for GMAO

This package generates comprehensive fine-tuning datasets from GMAO maintenance data.

## Features

- **12 Dataset Types**: QA, Instructions, Classifications, Summarizations, Predictions, Diagnostics, Comparisons, Time-Series, Multi-Document, Conversations, Validations, Documentation
- **3 Output Formats**: Alpaca, ShareGPT, ChatML
- **7,000+ Samples**: Configurable sample sizes for each dataset type
- **Train/Val/Test Splits**: Automatic 80/10/10 splitting

## Installation

```bash
pip install pandas numpy
```

## Usage

### Quick Start

```python
python data_finetune/generate_all_datasets.py
```

### Custom Configuration

```python
from data_finetune.generate_all_datasets import FinetuneDatasetGenerator

generator = FinetuneDatasetGenerator()

# Generate with custom sample sizes
generator.generate_all(
    qa_samples=5000,
    instruction_samples=1000,
    # ... other parameters
)

# Save in all formats
generator.save_all_formats()

# Generate statistics
generator.generate_statistics()
```

## Output Structure

```
data_finetune/outputs/
├── qa_alpaca.json
├── qa_sharegpt.json
├── qa_chatml.json
├── instructions_alpaca.json
├── ...
├── combined_all_alpaca.json
├── combined_all_sharegpt.json
├── combined_all_chatml.json
├── train_alpaca.json
├── validation_alpaca.json
├── test_alpaca.json
└── dataset_statistics.json
```

## Dataset Types

1. **QA Pairs**: Factual, statistical, diagnostic, temporal, and cost-related questions
2. **Instructions**: Sorting, filtering, reporting, analysis, and calculation tasks
3. **Classifications**: Severity, urgency, patterns, and maintenance type classification
4. **Summarizations**: Daily, weekly, machine, and cost summaries
5. **Predictions**: Failure prediction, preventive recommendations, risk identification
6. **Diagnostics**: Symptom analysis, root cause identification, solution chains
7. **Comparisons**: Machine benchmarking, performance comparisons
8. **Time-Series**: Trend analysis, temporal patterns
9. **Multi-Document**: Cross-dataset reasoning, comprehensive analysis
10. **Conversations**: Multi-turn dialogues, progressive exploration
11. **Validations**: Data quality checks, consistency validation
12. **Documentation**: Technical procedures, standard operations

## Format Details

### Alpaca Format
```json
{
  "instruction": "task description",
  "input": "context or data",
  "output": "expected response"
}
```

### ShareGPT Format
```json
{
  "conversations": [
    {"from": "human", "value": "question"},
    {"from": "gpt", "value": "answer"}
  ]
}
```

### ChatML Format
```json
{
  "messages": [
    {"role": "system", "content": "system prompt"},
    {"role": "user", "content": "question"},
    {"role": "assistant", "content": "answer"}
  ]
}
```

## Customization

Edit `data_finetune/configs/config.py` to customize:
- Sample sizes per dataset type
- Output formats
- Data augmentation settings
- Quality filters

## Statistics

After generation, check `dataset_statistics.json` for:
- Total samples per type
- Average input/output lengths
- Data distribution
- Quality metrics

## License

MIT
