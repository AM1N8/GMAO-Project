"""
LLM Provider Factory
Manages provider selection and automatic fallback
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.services.rag.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    LLMMessage,
    ProviderStatus,
    ProviderHealthInfo
)
from app.services.rag.llm.ollama_provider import OllamaProvider
from app.services.rag.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for LLM providers with automatic fallback.
    
    Manages primary (Groq) and fallback (Ollama) providers,
    automatically switching when primary is unavailable.
    """
    
    # Health check cache duration
    HEALTH_CACHE_SECONDS = 30
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: str = "llama-3.1-70b-versatile",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "qwen2.5:3b",
        enable_fallback: bool = True,
        primary_provider: str = "groq"
    ):
        self.enable_fallback = enable_fallback
        self.primary_provider_name = primary_provider
        
        # Groq config
        self._groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self._groq_config = LLMConfig(
            model_name=groq_model,
            temperature=0.1,
            max_tokens=1024,
            timeout_seconds=30,
            retry_attempts=3
        )
        
        # Ollama config
        self._ollama_base_url = ollama_base_url
        self._ollama_config = LLMConfig(
            model_name=ollama_model,
            temperature=0.1,
            max_tokens=1024,
            timeout_seconds=120
        )
        
        # Provider instances
        self._groq_provider: Optional[GroqProvider] = None
        self._ollama_provider: Optional[OllamaProvider] = None
        
        # Health cache
        self._groq_health_cache: Optional[tuple[datetime, ProviderHealthInfo]] = None
        self._ollama_health_cache: Optional[tuple[datetime, ProviderHealthInfo]] = None
        
        # Statistics
        self._stats = {
            "groq_requests": 0,
            "ollama_requests": 0,
            "fallback_count": 0,
            "total_failures": 0
        }
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all configured providers"""
        
        success = False
        
        # Initialize Groq if API key available
        if self._groq_api_key:
            try:
                self._groq_provider = GroqProvider(
                    config=self._groq_config,
                    api_key=self._groq_api_key
                )
                groq_ok = await self._groq_provider.initialize()
                if groq_ok:
                    logger.info("Groq provider initialized successfully")
                    success = True
                else:
                    logger.warning("Groq provider failed to initialize")
                    self._groq_provider = None
            except Exception as e:
                logger.error(f"Error initializing Groq provider: {e}")
                self._groq_provider = None
        else:
            logger.info("No Groq API key configured, skipping Groq provider")
        
        # Initialize Ollama
        try:
            self._ollama_provider = OllamaProvider(
                config=self._ollama_config,
                base_url=self._ollama_base_url
            )
            ollama_ok = await self._ollama_provider.initialize()
            if ollama_ok:
                logger.info("Ollama provider initialized successfully")
                success = True
            else:
                logger.warning("Ollama provider failed to initialize")
                self._ollama_provider = None
        except Exception as e:
            logger.error(f"Error initializing Ollama provider: {e}")
            self._ollama_provider = None
        
        self._initialized = success
        
        if not success:
            logger.error("No LLM providers available!")
        
        return success
    
    async def get_provider(self) -> BaseLLMProvider:
        """
        Get the best available provider with fallback.
        
        Returns:
            Available LLM provider
            
        Raises:
            RuntimeError if no provider is available
        """
        
        if not self._initialized:
            raise RuntimeError("LLM Factory not initialized")
        
        # Determine provider order based on configuration
        if self.primary_provider_name == "groq":
            providers = [
                ("groq", self._groq_provider, self._check_groq_health),
                ("ollama", self._ollama_provider, self._check_ollama_health)
            ]
        else:
            providers = [
                ("ollama", self._ollama_provider, self._check_ollama_health),
                ("groq", self._groq_provider, self._check_groq_health)
            ]
        
        # Try providers in order
        for name, provider, health_check in providers:
            if provider is None:
                continue
            
            health = await health_check()
            
            if health.status == ProviderStatus.AVAILABLE:
                if name != self.primary_provider_name:
                    self._stats["fallback_count"] += 1
                    logger.info(f"Using fallback provider: {name}")
                return provider
            
            elif health.status == ProviderStatus.RATE_LIMITED:
                logger.warning(f"{name} is rate limited, trying fallback")
                continue
            
            else:
                logger.warning(f"{name} unavailable: {health.error_message}")
        
        # No provider available
        self._stats["total_failures"] += 1
        raise RuntimeError("No LLM provider available")
    
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using available provider with fallback.
        
        Args:
            messages: Chat messages
            temperature: Override temperature
            max_tokens: Override max tokens
            preferred_provider: Force specific provider (no fallback)
            **kwargs: Additional provider parameters
            
        Returns:
            LLMResponse from best available provider
        """
        
        # If specific provider requested
        if preferred_provider:
            if preferred_provider == "groq" and self._groq_provider:
                return await self._groq_provider.generate(
                    messages, temperature, max_tokens, **kwargs
                )
            elif preferred_provider == "ollama" and self._ollama_provider:
                return await self._ollama_provider.generate(
                    messages, temperature, max_tokens, **kwargs
                )
            else:
                raise ValueError(f"Requested provider '{preferred_provider}' not available")
        
        # Use automatic selection with fallback
        last_error = None
        
        provider = await self.get_provider()
        
        try:
            response = await provider.generate(
                messages, temperature, max_tokens, **kwargs
            )
            
            # Update stats
            if provider.provider_name == "groq":
                self._stats["groq_requests"] += 1
            else:
                self._stats["ollama_requests"] += 1
            
            return response
            
        except Exception as e:
            last_error = e
            logger.error(f"Provider {provider.provider_name} failed: {e}")
            
            # Try fallback if enabled
            if self.enable_fallback:
                fallback = await self._get_fallback_provider(provider.provider_name)
                if fallback:
                    logger.info(f"Retrying with fallback provider: {fallback.provider_name}")
                    self._stats["fallback_count"] += 1
                    
                    try:
                        return await fallback.generate(
                            messages, temperature, max_tokens, **kwargs
                        )
                    except Exception as fallback_error:
                        logger.error(f"Fallback provider also failed: {fallback_error}")
                        last_error = fallback_error
        
        self._stats["total_failures"] += 1
        raise RuntimeError(f"All providers failed: {last_error}")
    
    async def _get_fallback_provider(
        self,
        failed_provider: str
    ) -> Optional[BaseLLMProvider]:
        """Get fallback provider after primary fails"""
        
        if failed_provider == "groq" and self._ollama_provider:
            health = await self._check_ollama_health()
            if health.status == ProviderStatus.AVAILABLE:
                return self._ollama_provider
        
        elif failed_provider == "ollama" and self._groq_provider:
            health = await self._check_groq_health()
            if health.status == ProviderStatus.AVAILABLE:
                return self._groq_provider
        
        return None
    
    async def _check_groq_health(self) -> ProviderHealthInfo:
        """Check Groq health with caching"""
        if self._groq_provider is None:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message="Provider not configured"
            )
        
        # Check cache
        if self._groq_health_cache:
            cache_time, cached_health = self._groq_health_cache
            if datetime.now() - cache_time < timedelta(seconds=self.HEALTH_CACHE_SECONDS):
                return cached_health
        
        # Fresh health check
        health = await self._groq_provider.check_health()
        self._groq_health_cache = (datetime.now(), health)
        return health
    
    async def _check_ollama_health(self) -> ProviderHealthInfo:
        """Check Ollama health with caching"""
        if self._ollama_provider is None:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message="Provider not configured"
            )
        
        # Check cache
        if self._ollama_health_cache:
            cache_time, cached_health = self._ollama_health_cache
            if datetime.now() - cache_time < timedelta(seconds=self.HEALTH_CACHE_SECONDS):
                return cached_health
        
        # Fresh health check
        health = await self._ollama_provider.check_health()
        self._ollama_health_cache = (datetime.now(), health)
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """Get factory statistics"""
        return {
            **self._stats,
            "groq_available": self._groq_provider is not None,
            "ollama_available": self._ollama_provider is not None,
            "primary_provider": self.primary_provider_name,
            "fallback_enabled": self.enable_fallback
        }
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all providers"""
        groq_health = await self._check_groq_health()
        ollama_health = await self._check_ollama_health()
        
        return {
            "groq": {
                "status": groq_health.status.value,
                "latency_ms": groq_health.latency_ms,
                "error": groq_health.error_message
            },
            "ollama": {
                "status": ollama_health.status.value,
                "latency_ms": ollama_health.latency_ms,
                "error": ollama_health.error_message
            }
        }


# Global factory instance (initialized lazily)
_llm_factory: Optional[LLMProviderFactory] = None


async def get_llm_provider() -> BaseLLMProvider:
    """Get the best available LLM provider"""
    global _llm_factory
    
    if _llm_factory is None:
        # Import settings here to avoid circular imports
        from app.services.rag.config import rag_settings
        
        _llm_factory = LLMProviderFactory(
            groq_api_key=rag_settings.GROQ_API_KEY,
            groq_model=rag_settings.GROQ_MODEL,
            ollama_base_url=rag_settings.OLLAMA_BASE_URL,
            ollama_model=rag_settings.OLLAMA_MODEL,
            enable_fallback=rag_settings.ENABLE_FALLBACK,
            primary_provider=rag_settings.PRIMARY_LLM_PROVIDER
        )
        await _llm_factory.initialize()
    
    return await _llm_factory.get_provider()


async def get_llm_factory() -> LLMProviderFactory:
    """Get the global LLM factory instance"""
    global _llm_factory
    
    if _llm_factory is None:
        await get_llm_provider()  # Initializes factory
    
    return _llm_factory
