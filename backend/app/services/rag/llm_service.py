"""
LLM Service using Ollama
Handles text generation for RAG responses
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage, MessageRole

from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service for generating RAG responses"""
    
    def __init__(self):
        self.model_name = rag_settings.OLLAMA_MODEL
        self.base_url = rag_settings.OLLAMA_BASE_URL
        self.llm: Optional[Ollama] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Ollama LLM"""
        try:
            # Check if Ollama is available
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
            
            # Initialize LLM
            self.llm = Ollama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=rag_settings.LLM_TEMPERATURE,
                request_timeout=rag_settings.OLLAMA_TIMEOUT,
                additional_kwargs={
                    "num_predict": rag_settings.LLM_MAX_TOKENS,
                }
            )
            
            # Test generation
            test_response = await self.llm.acomplete("Hello")
            logger.info(f"LLM service initialized with {self.model_name}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            self._initialized = False
            return False
    
    async def generate_response(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response using query and retrieved context"""
        if not self._initialized:
            raise RuntimeError("LLM service not initialized")
        
        try:
            # Build context from chunks
            context_text = self._build_context(context_chunks)
            
            # Build prompt
            system_msg = system_prompt or rag_settings.LLM_SYSTEM_PROMPT
            user_prompt = self._build_user_prompt(query, context_text)
            
            # Create messages
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_msg),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            
            # Generate response
            response = await self.llm.achat(messages)
            
            # Extract confidence if available (model-dependent)
            confidence = self._extract_confidence(response)
            
            return {
                "response": response.message.content,
                "confidence_score": confidence,
                "model": self.model_name,
                "context_length": len(context_text)
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            
            # Format chunk with metadata
            chunk_text = f"[Source {i}]"
            
            if "filename" in metadata:
                chunk_text += f" (from {metadata['filename']})"
            
            if "page_number" in metadata:
                chunk_text += f" [Page {metadata['page_number']}]"
            
            chunk_text += f"\n{text}\n"
            context_parts.append(chunk_text)
        
        return "\n---\n".join(context_parts)
    
    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build user prompt with query and context"""
        prompt = f"""Use the following context to answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
        return prompt
    
    def _extract_confidence(self, response: Any) -> Optional[float]:
        """Extract confidence score from response if available"""
        # This is model-dependent and may not be available
        # For now, return None
        return None
    
    async def generate_simple(self, prompt: str) -> str:
        """Generate a simple text completion"""
        if not self._initialized:
            raise RuntimeError("LLM service not initialized")
        
        try:
            response = await self.llm.acomplete(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error in simple generation: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False
    
    def truncate_context(self, context: str, max_tokens: Optional[int] = None) -> str:
        """Truncate context to fit within token limit"""
        max_tokens = max_tokens or rag_settings.MAX_CONTEXT_LENGTH
        
        # Rough approximation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(context) <= max_chars:
            return context
        
        # Truncate and add ellipsis
        truncated = context[:max_chars - 50]
        return truncated + "\n\n[Context truncated due to length...]"


# Global LLM service instance
llm_service = LLMService()