"""
Guidance Router
Exposes endpoints for the AI Guidance Agent.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.schemas import (
    GuidanceAskRequest,
    GuidanceAskResponse,
    SuggestActionRequest,
    SuggestActionResponse,
    PageHelpResponse,
    ExplainErrorRequest,
    ExplainErrorResponse
)
from app.services.guidance_service import guidance_service

router = APIRouter()


@router.post(
    "/ask",
    response_model=GuidanceAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the Guidance Agent a Question",
    description="""
    Ask the AI Guidance Agent a natural language question about using the GMAO system.
    
    The agent provides context-aware assistance including:
    - Step-by-step instructions for tasks
    - Feature explanations
    - Navigation help
    - Troubleshooting advice
    
    The response includes suggested next actions and related page links.
    """
)
async def ask_guidance(
    request: GuidanceAskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Answer a user's guidance question.
    Requires authentication.
    """
    try:
        response = await guidance_service.ask_guidance(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing guidance request: {str(e)}"
        )


@router.post(
    "/suggest-action",
    response_model=SuggestActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Suggested Actions for Current Page",
    description="""
    Get contextual action suggestions based on the current page and optional user intent.
    
    Returns a list of suggested actions the user can take, prioritized by relevance.
    Each suggestion includes:
    - Action name and description
    - Priority level
    - UI element to interact with
    - Target route (if navigation is needed)
    """
)
async def suggest_action(
    request: SuggestActionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get suggested actions for the current page.
    Requires authentication.
    """
    try:
        response = await guidance_service.suggest_actions(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting action suggestions: {str(e)}"
        )


@router.get(
    "/page-help/{page_route:path}",
    response_model=PageHelpResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Help for a Specific Page",
    description="""
    Get comprehensive help information for a specific page.
    
    Returns:
    - Page name and description
    - Key features available on the page
    - Common tasks users perform
    - All available actions with details
    - Helpful tips for using the page
    
    Example page routes:
    - home/equipment
    - home/interventions
    - home/kpi
    """
)
async def get_page_help(
    page_route: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed help for a specific page.
    Requires authentication.
    """
    try:
        # Normalize page route (add leading slash if missing)
        if not page_route.startswith("/"):
            page_route = "/" + page_route
        
        response = await guidance_service.get_page_help(page_route)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting page help: {str(e)}"
        )


@router.post(
    "/explain-error",
    response_model=ExplainErrorResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain an Error Message",
    description="""
    Get a user-friendly explanation of an error message.
    
    The agent will:
    - Translate technical errors into simple language
    - Explain the likely cause
    - Provide step-by-step recovery instructions
    - Suggest how to prevent the error in the future
    - Indicate the severity level (critical/warning/info)
    
    This helps users understand and resolve errors without needing technical knowledge.
    """
)
async def explain_error(
    request: ExplainErrorRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Explain an error message in user-friendly terms.
    Requires authentication.
    """
    try:
        response = await guidance_service.explain_error(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error explaining error: {str(e)}"
        )
