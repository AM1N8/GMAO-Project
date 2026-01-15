import json
import os
from fastapi import APIRouter, HTTPException
from app.services.rag.llm_service import llm_service
from app.schemas import SimpleChatRequest, SimpleChatResponse
from llama_index.core.llms import ChatMessage, MessageRole

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Relative path from backend folder
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "../../data/prompts/prompt.json")


def load_system_prompt() -> str:
    """Load system prompt from JSON file locally"""
    if not os.path.exists(PROMPT_FILE):
        return "You are a helpful AI assistant."  # fallback

    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("system_prompt", "You are a helpful AI assistant.")
    except Exception:
        return "You are a helpful AI assistant."


# ============================================================================

@router.post("/simple", response_model=SimpleChatResponse)
async def simple_chat(payload: SimpleChatRequest):
    """Simple LLM query without system prompt"""
    if not llm_service._initialized:
        ok = await llm_service.initialize()
        if not ok:
            raise HTTPException(status_code=500, detail="LLM unavailable")

    try:
        text = await llm_service.generate_simple(payload.prompt)
        return SimpleChatResponse(response=text, model=llm_service.model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================

@router.post("/qna", response_model=SimpleChatResponse)
async def chatbot_qna(payload: SimpleChatRequest):
    """Chatbot using system prompt from local prompt.json"""
    if not llm_service._initialized:
        ok = await llm_service.initialize()
        if not ok:
            raise HTTPException(status_code=500, detail="LLM unavailable")

    try:
        system_prompt = load_system_prompt()

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=payload.prompt)
        ]

        result = await llm_service.llm.achat(messages)

        return SimpleChatResponse(response=result.message.content, model=llm_service.model_name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
