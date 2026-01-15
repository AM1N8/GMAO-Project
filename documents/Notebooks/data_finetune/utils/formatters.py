"""
data_finetune/utils/formatters.py

Formatters for different LLM fine-tuning formats (Alpaca, ShareGPT, ChatML).
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod


class BaseFormatter(ABC):
    """Base class for formatters."""
    
    @abstractmethod
    def format_single(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single training example."""
        pass
    
    def format_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format a batch of training examples."""
        return [self.format_single(item) for item in items]


class AlpacaFormatter(BaseFormatter):
    """Alpaca format: instruction, input, output."""
    
    def format_single(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "instruction": item.get('instruction', ''),
            "input": item.get('input', ''),
            "output": item.get('output', ''),
            "metadata": {
                "dataset_type": item.get('dataset_type', ''),
                "source": "GMAO"
            }
        }


class ShareGPTFormatter(BaseFormatter):
    """ShareGPT format: conversations with roles."""
    
    def format_single(self, item: Dict[str, Any]) -> Dict[str, Any]:
        conversations = []
        
        # System message (optional)
        if item.get('system'):
            conversations.append({
                "from": "system",
                "value": item['system']
            })
        
        # User message
        user_content = item.get('instruction', '')
        if item.get('input'):
            user_content += f"\n\n{item['input']}"
        
        conversations.append({
            "from": "human",
            "value": user_content
        })
        
        # Assistant response
        conversations.append({
            "from": "gpt",
            "value": item.get('output', '')
        })
        
        # Handle multi-turn conversations
        if 'conversation' in item:
            for turn in item['conversation']:
                conversations.append({
                    "from": "human" if turn['role'] == 'user' else "gpt",
                    "value": turn['content']
                })
        
        return {
            "conversations": conversations,
            "metadata": {
                "dataset_type": item.get('dataset_type', ''),
                "source": "GMAO"
            }
        }


class ChatMLFormatter(BaseFormatter):
    """ChatML format: messages with roles."""
    
    def format_single(self, item: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        
        # System message
        system_msg = item.get('system', 
            "You are an expert GMAO (Maintenance Management) assistant. "
            "You help analyze maintenance data, diagnose problems, and provide insights.")
        messages.append({
            "role": "system",
            "content": system_msg
        })
        
        # User message
        user_content = item.get('instruction', '')
        if item.get('input'):
            user_content += f"\n\n{item['input']}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Assistant response
        messages.append({
            "role": "assistant",
            "content": item.get('output', '')
        })
        
        # Handle multi-turn conversations
        if 'conversation' in item:
            for turn in item['conversation']:
                messages.append({
                    "role": turn['role'],
                    "content": turn['content']
                })
        
        return {
            "messages": messages,
            "metadata": {
                "dataset_type": item.get('dataset_type', ''),
                "source": "GMAO"
            }
        }


class JSONLFormatter(BaseFormatter):
    """JSONL format: one JSON object per line."""
    
    def format_single(self, item: Dict[str, Any]) -> str:
        """Return JSON string (for JSONL)."""
        import json
        formatted = AlpacaFormatter().format_single(item)
        return json.dumps(formatted, ensure_ascii=False)
    
    def format_batch(self, items: List[Dict[str, Any]]) -> str:
        """Return JSONL string."""
        return '\n'.join([self.format_single(item) for item in items])