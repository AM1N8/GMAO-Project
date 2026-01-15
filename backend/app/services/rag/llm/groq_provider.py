"""
Groq LLM Provider
Implements BaseLLMProvider for Groq cloud API
"""

import logging
import time
import asyncio
from typing import List, Optional
from datetime import datetime

from app.services.rag.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    ProviderHealthInfo,
    ProviderStatus
)

logger = logging.getLogger(__name__)

# Try to import groq, gracefully handle if not installed
try:
    from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq package not installed. Install with: pip install groq")


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider for fast cloud inference.
    
    Primary provider with automatic retry and rate limit handling.
    """
    
    def __init__(
        self,
        config: LLMConfig,
        api_key: str
    ):
        super().__init__(config)
        self.api_key = api_key
        self._client: Optional["AsyncGroq"] = None
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[datetime] = None
    
    @property
    def provider_name(self) -> str:
        return "groq"
    
    async def initialize(self) -> bool:
        """Initialize Groq client and verify API key"""
        
        if not GROQ_AVAILABLE:
            logger.error("Groq package not installed")
            return False
        
        if not self.api_key:
            logger.error("Groq API key not provided")
            return False
        
        try:
            self._client = AsyncGroq(api_key=self.api_key)
            
            # Test with a minimal request
            test_response = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            
            if not test_response or not test_response.choices:
                raise RuntimeError("Empty response from Groq test")
            
            self._initialized = True
            logger.info(
                f"Groq provider initialized with model {self.config.model_name}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {e}")
            self._initialized = False
            return False
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Groq API with retry logic"""
        
        if not self._initialized or not self._client:
            raise RuntimeError("Groq provider not initialized")
        
        start_time = time.time()
        
        # Convert messages to Groq format
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Determine parameters
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        last_error = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = await self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=groq_messages,
                    temperature=temp,
                    max_tokens=tokens,
                    **kwargs
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Extract usage info
                usage = response.usage
                
                # Build response
                llm_response = LLMResponse(
                    content=response.choices[0].message.content,
                    model_name=self.config.model_name,
                    provider_name=self.provider_name,
                    tokens_used=usage.total_tokens if usage else None,
                    prompt_tokens=usage.prompt_tokens if usage else None,
                    completion_tokens=usage.completion_tokens if usage else None,
                    latency_ms=latency_ms,
                    finish_reason=response.choices[0].finish_reason,
                    metadata={
                        "response_id": response.id,
                        "model": response.model
                    }
                )
                
                self._log_request(messages, llm_response)
                return llm_response
                
            except RateLimitError as e:
                last_error = e
                logger.warning(
                    f"Groq rate limit hit, attempt {attempt + 1}/{self.config.retry_attempts}"
                )
                # Update rate limit info
                self._rate_limit_remaining = 0
                
                if attempt < self.config.retry_attempts - 1:
                    # Exponential backoff
                    wait_time = self.config.retry_delay_seconds * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    
            except APIConnectionError as e:
                last_error = e
                logger.error(f"Groq connection error: {e}")
                break  # Don't retry connection errors
                
            except APIStatusError as e:
                last_error = e
                logger.error(f"Groq API error: {e.status_code} - {e.message}")
                
                if e.status_code >= 500:
                    # Server error, retry
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    # Client error, don't retry
                    break
                    
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error in Groq generate: {e}")
                break
        
        # All retries failed
        self._log_request(messages, error=last_error)
        raise last_error if last_error else RuntimeError("Groq generation failed")
    
    async def check_health(self) -> ProviderHealthInfo:
        """Check Groq API availability"""
        
        if not GROQ_AVAILABLE:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message="Groq package not installed"
            )
        
        if not self.api_key:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message="No API key configured"
            )
        
        try:
            start_time = time.time()
            
            # Create temporary client if not initialized
            client = self._client or AsyncGroq(api_key=self.api_key)
            
            # Minimal health check request
            response = await client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            self._last_health_check = ProviderHealthInfo(
                status=ProviderStatus.AVAILABLE,
                last_check=datetime.now(),
                latency_ms=latency_ms,
                rate_limit_remaining=self._rate_limit_remaining
            )
            return self._last_health_check
            
        except RateLimitError:
            return ProviderHealthInfo(
                status=ProviderStatus.RATE_LIMITED,
                last_check=datetime.now(),
                rate_limit_remaining=0,
                rate_limit_reset_at=self._rate_limit_reset
            )
        except APIConnectionError:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message="Cannot connect to Groq API"
            )
        except Exception as e:
            return ProviderHealthInfo(
                status=ProviderStatus.ERROR,
                last_check=datetime.now(),
                error_message=str(e)
            )
