"""
LLM Provider Package
Provides unified interface for multiple LLM backends with fallback support
"""

# Lazy imports to avoid circular dependencies on startup
def __getattr__(name):
    if name == "BaseLLMProvider":
        from app.services.rag.llm.base import BaseLLMProvider
        return BaseLLMProvider
    elif name == "LLMResponse":
        from app.services.rag.llm.base import LLMResponse
        return LLMResponse
    elif name == "ProviderStatus":
        from app.services.rag.llm.base import ProviderStatus
        return ProviderStatus
    elif name == "LLMConfig":
        from app.services.rag.llm.base import LLMConfig
        return LLMConfig
    elif name == "LLMProviderFactory":
        from app.services.rag.llm.provider_factory import LLMProviderFactory
        return LLMProviderFactory
    elif name == "get_llm_provider":
        from app.services.rag.llm.provider_factory import get_llm_provider
        return get_llm_provider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseLLMProvider",
    "LLMResponse", 
    "ProviderStatus",
    "LLMConfig",
    "LLMProviderFactory",
    "get_llm_provider"
]

