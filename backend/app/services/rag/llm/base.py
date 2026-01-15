"""
Base LLM Provider Interface
Defines abstract interface for all LLM providers (Groq, Ollama, etc.)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """LLM Provider health status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    INITIALIZING = "initializing"


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout_seconds: int = 60
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class LLMMessage:
    """Chat message format"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    model_name: str
    provider_name: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: float = 0.0
    cached: bool = False
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        if self.tokens_used:
            return self.tokens_used
        if self.prompt_tokens and self.completion_tokens:
            return self.prompt_tokens + self.completion_tokens
        return 0


@dataclass
class ProviderHealthInfo:
    """Health information for a provider"""
    status: ProviderStatus
    last_check: datetime
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_at: Optional[datetime] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement this interface to ensure
    consistent behavior across different backends.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._initialized = False
        self._last_health_check: Optional[ProviderHealthInfo] = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g., 'groq', 'ollama')"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider connection.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of chat messages (system, user, assistant)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with generated content and metadata
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> ProviderHealthInfo:
        """
        Check if the provider is available and healthy.
        
        Returns:
            ProviderHealthInfo with current status
        """
        pass
    
    async def is_available(self) -> bool:
        """Quick check if provider is available"""
        try:
            health = await self.check_health()
            return health.status == ProviderStatus.AVAILABLE
        except Exception:
            return False
    
    def get_model_name(self) -> str:
        """Get the current model name"""
        return self.config.model_name
    
    async def generate_simple(self, prompt: str, **kwargs) -> str:
        """
        Convenience method for simple text generation.
        
        Args:
            prompt: User prompt text
            **kwargs: Additional parameters
            
        Returns:
            Generated text content
        """
        messages = [LLMMessage(role="user", content=prompt)]
        response = await self.generate(messages, **kwargs)
        return response.content
    
    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate with explicit system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query/request
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with generated content
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        return await self.generate(messages, **kwargs)
    
    def _log_request(
        self,
        messages: List[LLMMessage],
        response: Optional[LLMResponse] = None,
        error: Optional[Exception] = None
    ):
        """Log request for observability"""
        log_data = {
            "provider": self.provider_name,
            "model": self.config.model_name,
            "message_count": len(messages),
        }
        
        if response:
            log_data.update({
                "latency_ms": response.latency_ms,
                "tokens": response.total_tokens,
                "cached": response.cached
            })
            logger.info(f"LLM request completed", extra=log_data)
        elif error:
            log_data["error"] = str(error)
            logger.error(f"LLM request failed", extra=log_data)
