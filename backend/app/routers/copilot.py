"""
Copilot Router
Exposes endpoints for the AI Maintenance Copilot.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.schemas import CopilotQueryRequest, CopilotQueryResponse
from app.services.copilot_service import copilot_service

router = APIRouter()

@router.post(
    "/query",
    response_model=CopilotQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the Maintenance Copilot",
    description="""
    Send a natural language query to the Maintenance Copilot.
    
    The Copilot will:
    1. Detect the intent (KPI Explanation, Equipment Health, or Intervention Report)
    2. Retrieve relevant data from the database (KPIs, histories, AMDEC)
    3. Use AI to reason about the data and generate a structured response
    
    Returns structured data including summary, detailed explanation, and recommended actions.
    """
)
async def query_copilot(
    request: CopilotQueryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Process a Copilot query.
    Requires authentication.
    """
    try:
        response = await copilot_service.process_query(db, request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
