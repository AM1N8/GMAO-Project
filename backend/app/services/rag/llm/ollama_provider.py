"""
Ollama LLM Provider
Implements BaseLLMProvider for local Ollama models
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

import httpx
from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage, MessageRole

from app.services.rag.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    ProviderHealthInfo,
    ProviderStatus
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM provider for local model inference.
    
    Uses llama-index Ollama integration for compatibility
    with existing codebase.
    """
    
    def __init__(
        self,
        config: LLMConfig,
        base_url: str = "http://localhost:11434"
    ):
        super().__init__(config)
        self.base_url = base_url
        self._llm: Optional[Ollama] = None
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    async def initialize(self) -> bool:
        """Initialize Ollama connection and verify model availability"""
        try:
            # Check if Ollama is running
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
            
            # Initialize LlamaIndex Ollama wrapper
            self._llm = Ollama(
                model=self.config.model_name,
                base_url=self.base_url,
                temperature=self.config.temperature,
                request_timeout=self.config.timeout_seconds,
                additional_kwargs={
                    "num_predict": self.config.max_tokens,
                }
            )
            
            # Test with a simple request
            test_response = await self._llm.acomplete("Hello")
            if not test_response or not test_response.text:
                raise RuntimeError("Empty response from Ollama test")
            
            self._initialized = True
            logger.info(
                f"Ollama provider initialized with model {self.config.model_name}"
            )
            return True
            
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            self._initialized = False
            return False
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Ollama"""
        
        if not self._initialized or not self._llm:
            raise RuntimeError("Ollama provider not initialized")
        
        start_time = time.time()
        
        try:
            # Convert to LlamaIndex message format
            chat_messages = self._convert_messages(messages)
            
            # Apply temperature override if provided
            if temperature is not None:
                self._llm.temperature = temperature
            else:
                self._llm.temperature = self.config.temperature
            
            # Generate response
            response = await self._llm.achat(chat_messages)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Build response object
            llm_response = LLMResponse(
                content=response.message.content,
                model_name=self.config.model_name,
                provider_name=self.provider_name,
                latency_ms=latency_ms,
                finish_reason="stop",
                metadata={
                    "raw_response": str(response.raw) if hasattr(response, 'raw') else None
                }
            )
            
            self._log_request(messages, llm_response)
            return llm_response
            
        except Exception as e:
            self._log_request(messages, error=e)
            raise
    
    async def check_health(self) -> ProviderHealthInfo:
        """Check Ollama availability"""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if our model is available
            tags_data = response.json()
            available_models = [m.get("name") for m in tags_data.get("models", [])]
            
            # Ollama returns model names with tags like "qwen2.5:3b"
            model_available = any(
                self.config.model_name in model_name 
                for model_name in available_models
            )
            
            if not model_available:
                return ProviderHealthInfo(
                    status=ProviderStatus.ERROR,
                    last_check=datetime.now(),
                    latency_ms=latency_ms,
                    error_message=f"Model {self.config.model_name} not found. Available: {available_models}"
                )
            
            self._last_health_check = ProviderHealthInfo(
                status=ProviderStatus.AVAILABLE,
                last_check=datetime.now(),
                latency_ms=latency_ms
            )
            return self._last_health_check
            
        except httpx.ConnectError:
            return ProviderHealthInfo(
                status=ProviderStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_message=f"Cannot connect to Ollama at {self.base_url}"
            )
        except Exception as e:
            return ProviderHealthInfo(
                status=ProviderStatus.ERROR,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[ChatMessage]:
        """Convert our message format to LlamaIndex format"""
        role_map = {
            "system": MessageRole.SYSTEM,
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT
        }
        
        return [
            ChatMessage(
                role=role_map.get(msg.role, MessageRole.USER),
                content=msg.content
            )
            for msg in messages
        ]
