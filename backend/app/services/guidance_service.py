"""
Guidance Agent Service
Provides context-aware assistance to users navigating the GMAO system.
"""

import json
import os
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

from app.services.rag.llm.provider_factory import get_llm_factory
from app.services.rag.llm.base import LLMMessage
from app.schemas import (
    GuidanceContext,
    GuidanceAskRequest,
    GuidanceAskResponse,
    GuidanceSuggestedAction,
    GuidanceRelatedLink,
    SuggestActionRequest,
    SuggestActionResponse,
    PageHelpResponse,
    ExplainErrorRequest,
    ExplainErrorResponse,
    RecoveryStep
)

logger = logging.getLogger(__name__)


class GuidanceService:
    """
    Service for providing context-aware guidance to users.
    
    Uses Groq LLM to understand user questions and generate helpful responses.
    Integrates with page mappings to provide accurate, context-specific guidance.
    """
    
    def __init__(self):
        self.page_mappings: Dict[str, Any] = {}
        self._load_page_mappings()
    
    def _load_page_mappings(self):
        """Load page mappings from JSON file"""
        try:
            mappings_path = Path(__file__).parent.parent.parent / "data" / "guidance" / "page_mappings.json"
            if mappings_path.exists():
                with open(mappings_path, 'r', encoding='utf-8') as f:
                    self.page_mappings = json.load(f)
                logger.info(f"Loaded page mappings for {len(self.page_mappings)} pages")
            else:
                logger.warning(f"Page mappings file not found: {mappings_path}")
        except Exception as e:
            logger.error(f"Error loading page mappings: {e}")
    
    async def ask_guidance(self, request: GuidanceAskRequest) -> GuidanceAskResponse:
        """
        Answer a user's guidance question with context-aware assistance.
        
        Args:
            request: Question and user context
            
        Returns:
            Answer with suggested actions and related links
        """
        try:
            # Get page info
            page_info = self.page_mappings.get(request.context.current_page, {})
            page_name = page_info.get("page_name", "Unknown Page")
            
            # Classify question type
            response_type = await self._classify_question_type(request.question)
            
            # Build context for LLM
            context_str = self._build_context_string(request.context, page_info)
            
            # Generate answer using LLM
            answer_data = await self._generate_answer(
                question=request.question,
                context=context_str,
                response_type=response_type
            )
            
            # Extract suggested actions and links based on question
            suggested_actions = await self._extract_suggested_actions(
                question=request.question,
                answer=answer_data["answer"],
                page_info=page_info,
                response_type=response_type
            )
            
            related_links = self._extract_related_links(
                page_info=page_info,
                response_type=response_type
            )
            
            return GuidanceAskResponse(
                answer=answer_data["answer"],
                suggested_actions=suggested_actions,
                related_links=related_links,
                confidence=answer_data["confidence"],
                response_type=response_type
            )
            
        except Exception as e:
            logger.error(f"Error in ask_guidance: {e}")
            # Return fallback response
            return GuidanceAskResponse(
                answer="I'm sorry, I'm having trouble answering that question right now. Please try rephrasing or contact support.",
                suggested_actions=[],
                related_links=[],
                confidence="low",
                response_type="general"
            )
    
    async def suggest_actions(self, request: SuggestActionRequest) -> SuggestActionResponse:
        """
        Suggest contextual actions based on current page.
        
        Args:
            request: Current page and optional user intent
            
        Returns:
            Suggested actions for the current page
        """
        try:
            page_info = self.page_mappings.get(request.current_page, {})
            
            if not page_info:
                # Unknown page - return generic suggestion
                return SuggestActionResponse(
                    suggestions=[],
                    page_name="Unknown Page",
                    page_description="This page is not recognized in the system."
                )
            
            # Convert page mappings to suggestions
            suggestions: List[GuidanceSuggestedAction] = []
            
            for action_info in page_info.get("available_actions", [])[:5]:  # Top 5 actions
                # Determine priority based on user intent or action importance
                priority = "high" if request.user_intent and request.user_intent.lower() in action_info.get("description", "").lower() else "medium"
                
                suggestions.append(GuidanceSuggestedAction(
                    action_name=action_info.get("description", "Unknown Action"),
                    description=action_info.get("description", ""),
                    priority=priority,
                    ui_element=action_info.get("ui_element"),
                    target_route=None  # Same page
                ))
            
            return SuggestActionResponse(
                suggestions=suggestions,
                page_name=page_info.get("page_name", "Unknown Page"),
                page_description=page_info.get("description")
            )
            
        except Exception as e:
            logger.error(f"Error in suggest_actions: {e}")
            return SuggestActionResponse(
                suggestions=[],
                page_name="Error",
                page_description="Unable to load page suggestions."
            )
    
    async def get_page_help(self, page_route: str) -> PageHelpResponse:
        """
        Get comprehensive help for a specific page.
        
        Args:
            page_route: Page route (e.g., '/home/equipment')
            
        Returns:
            Detailed page help information
        """
        try:
            page_info = self.page_mappings.get(page_route, {})
            
            if not page_info:
                return PageHelpResponse(
                    page_name="Unknown Page",
                    description="This page is not recognized.",
                    key_features=[],
                    common_tasks=[],
                    available_actions=[],
                    tips=[]
                )
            
            # Convert actions to GuidanceSuggestedAction format
            available_actions: List[GuidanceSuggestedAction] = []
            for action_info in page_info.get("available_actions", []):
                available_actions.append(GuidanceSuggestedAction(
                    action_name=action_info.get("action", "Unknown"),
                    description=action_info.get("description", ""),
                    priority="medium",
                    ui_element=action_info.get("ui_element"),
                    target_route=None
                ))
            
            # Extract key features and common tasks from actions
            key_features = [action.get("description", "") for action in page_info.get("available_actions", [])[:3]]
            common_tasks = [f"Use the {action.get('ui_element', 'relevant control')} to {action.get('description', '').lower()}" 
                          for action in page_info.get("available_actions", [])[:3]]
            
            # Generate tips using LLM
            tips = await self._generate_page_tips(page_info)
            
            return PageHelpResponse(
                page_name=page_info.get("page_name", "Unknown Page"),
                description=page_info.get("description", ""),
                key_features=key_features,
                common_tasks=common_tasks,
                available_actions=available_actions,
                tips=tips
            )
            
        except Exception as e:
            logger.error(f"Error in get_page_help: {e}")
            raise
    
    async def explain_error(self, request: ExplainErrorRequest) -> ExplainErrorResponse:
        """
        Explain an error message in user-friendly terms.
        
        Args:
            request: Error message and context
            
        Returns:
            Simplified explanation with recovery steps
        """
        try:
            # Use LLM to explain the error
            explanation_data = await self._generate_error_explanation(
                error_message=request.error_message,
                context=request.context,
                error_code=request.error_code
            )
            
            return ExplainErrorResponse(
                simplified_explanation=explanation_data["explanation"],
                likely_cause=explanation_data["cause"],
                recovery_steps=explanation_data["recovery_steps"],
                prevention_tip=explanation_data.get("prevention_tip"),
                severity=explanation_data["severity"]
            )
            
        except Exception as e:
            logger.error(f"Error in explain_error: {e}")
            # Fallback response
            return ExplainErrorResponse(
                simplified_explanation="An error occurred. Please try again or contact support.",
                likely_cause="Unknown error",
                recovery_steps=[
                    RecoveryStep(
                        step_number=1,
                        instruction="Refresh the page and try again",
                        ui_element="Browser Refresh Button"
                    )
                ],
                prevention_tip="Make sure you're using the latest version of the application.",
                severity="warning"
            )
    
    # ==================== Private Helper Methods ====================
    
    def _build_context_string(self, context: GuidanceContext, page_info: Dict[str, Any]) -> str:
        """Build context string for LLM"""
        parts = []
        
        parts.append(f"Current Page: {page_info.get('page_name', 'Unknown')}")
        parts.append(f"Page Description: {page_info.get('description', '')}")
        
        if context.user_role:
            parts.append(f"User Role: {context.user_role}")
        
        if context.recent_actions:
            parts.append(f"Recent Actions: {', '.join(context.recent_actions[-3:])}")
        
        if page_info.get("available_actions"):
            actions_list = ", ".join([action.get("description", "") for action in page_info["available_actions"][:5]])
            parts.append(f"Available Actions: {actions_list}")
        
        return "\n".join(parts)
    
    async def _classify_question_type(self, question: str) -> str:
        """Classify the type of question"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["how to", "how do i", "how can i"]):
            return "how_to"
        elif any(word in question_lower for word in ["where", "find", "locate"]):
            return "navigation"
        elif any(word in question_lower for word in ["what is", "explain", "describe"]):
            return "feature_explanation"
        elif any(word in question_lower for word in ["error", "problem", "issue", "fix"]):
            return "troubleshooting"
        else:
            return "general"
    
    async def _generate_answer(self, question: str, context: str, response_type: str) -> Dict[str, Any]:
        """Generate answer using LLM"""
        try:
            llm_factory = await get_llm_factory()
            
            # Build prompt based on question type
            system_prompt = self._get_system_prompt(response_type)
            user_prompt = f"""Context:
{context}

User Question: {question}

Please provide a clear, helpful answer. Keep it concise (under 150 words unless detailed steps are needed).
If providing step-by-step instructions, use numbered list format."""
            
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]
            
            response = await llm_factory.generate(messages=messages, temperature=0.3, max_tokens=300)
            
            # Determine confidence based on response quality
            confidence = "high" if len(response.content) > 50 else "medium"
            
            return {
                "answer": response.content.strip(),
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer": "I'm having trouble generating an answer right now. Please try again or contact support.",
                "confidence": "low"
            }
    
    def _get_system_prompt(self, response_type: str) -> str:
        """Get system prompt based on response type"""
        base_prompt = """You are an AI guidance assistant for a Maintenance Management (GMAO/CMMS) system.
Your role is to help users navigate the system and accomplish their tasks.

Guidelines:
- Be concise but complete
- Use clear, simple language
- Reference specific UI elements (buttons, menus, forms) when relevant
- Be friendly and helpful"""
        
        if response_type == "how_to":
            return base_prompt + "\n- Provide step-by-step instructions\n- Start each step with a number\n- Mention which UI element to use for each step"
        elif response_type == "navigation":
            return base_prompt + "\n- Direct the user to the correct page or feature\n- Mention the menu path or navigation steps"
        elif response_type == "feature_explanation":
            return base_prompt + "\n- Explain what the feature does\n- Provide a use case or example\n- Mention any prerequisites"
        elif response_type == "troubleshooting":
            return base_prompt + "\n- Acknowledge the issue\n- Suggest possible solutions\n- Prioritize the most common fixes first"
        else:
            return base_prompt
    
    async def _extract_suggested_actions(
        self,
        question: str,
        answer: str,
        page_info: Dict[str, Any],
        response_type: str
    ) -> List[GuidanceSuggestedAction]:
        """Extract relevant suggested actions based on the question and answer"""
        suggestions: List[GuidanceSuggestedAction] = []
        
        # Get related actions from page info
        related_actions = page_info.get("available_actions", [])
        
        # For how_to questions, suggest the primary action
        if response_type == "how_to" and related_actions:
            # Try to find the most relevant action based on question keywords
            question_lower = question.lower()
            
            for action_info in related_actions[:3]:
                action_desc = action_info.get("description", "").lower()
                if any(word in action_desc for word in question_lower.split() if len(word) > 3):
                    suggestions.append(GuidanceSuggestedAction(
                        action_name=action_info.get("description", ""),
                        description=f"Use the {action_info.get('ui_element', 'relevant control')}",
                        priority="high",
                        ui_element=action_info.get("ui_element"),
                        target_route=None
                    ))
                    break
        
        # For navigation questions, suggest related pages
        if response_type == "navigation":
            related_pages = page_info.get("related_pages", [])
            for page_route in related_pages[:2]:
                page_data = self.page_mappings.get(page_route, {})
                if page_data:
                    suggestions.append(GuidanceSuggestedAction(
                        action_name=f"Go to {page_data.get('page_name', '')}",
                        description=page_data.get("description", ""),
                        priority="medium",
                        ui_element="Navigation Menu",
                        target_route=page_route
                    ))
        
        # Add up to 2 general suggestions from current page
        if len(suggestions)  < 2 and related_actions:
            for action_info in related_actions[:2-len(suggestions)]:
                suggestions.append(GuidanceSuggestedAction(
                    action_name=action_info.get("description", ""),
                    description=f"Use the {action_info.get('ui_element', 'relevant control')}",
                    priority="low",
                    ui_element=action_info.get("ui_element"),
                    target_route=None
                ))
        
        return suggestions
    
    def _extract_related_links(self, page_info: Dict[str, Any], response_type: str) -> List[GuidanceRelatedLink]:
        """Extract related page links"""
        links: List[GuidanceRelatedLink] = []
        
        related_pages = page_info.get("related_pages", [])
        for page_route in related_pages[:3]:
            page_data = self.page_mappings.get(page_route, {})
            if page_data:
                links.append(GuidanceRelatedLink(
                    title=page_data.get("page_name", ""),
                    route=page_route,
                    description=page_data.get("description", "")
                ))
        
        return links
    
    async def _generate_page_tips(self, page_info: Dict[str, Any]) -> List[str]:
        """Generate helpful tips for a page"""
        # For now, return static tips based on page type
        # Could be enhanced with LLM generation
        tips = [
            f"Use the search or filter features to quickly find what you need",
            f"You can export data from this page for offline analysis"
        ]
        
        return tips
    
    async def _generate_error_explanation(
        self,
        error_message: str,
        context: GuidanceContext,
        error_code: Optional[str]
    ) -> Dict[str, Any]:
        """Generate error explanation using LLM"""
        try:
            llm_factory = await get_llm_factory()
            
            # Context for error
            page_info = self.page_mappings.get(context.current_page, {})
            page_name = page_info.get("page_name", "Unknown Page")
            
            system_prompt = """You are a helpful technical support assistant for a maintenance management system.
Your role is to explain errors in simple, non-technical language and provide clear recovery steps.

Guidelines:
- Use simple language, avoid jargon
- Be empathetic and reassuring
- Provide specific, actionable steps
- Prioritize the most likely solution first"""
            
            user_prompt = f"""Page: {page_name}
Error Message: {error_message}
{f"Error Code: {error_code}" if error_code else ""}

Please provide:
1. A simple explanation of what went wrong (1-2 sentences)
2. The most likely cause
3. Step-by-step recovery instructions (maximum 4 steps)
4. A tip to prevent this error in the future
5. Severity level (critical/warning/info)

Format your response as JSON:
{{
    "explanation": "...",
    "cause": "...",
    "recovery_steps": [
        {{"step_number": 1, "instruction": "...", "ui_element": "..."}},
        ...
    ],
    "prevention_tip": "...",
    "severity": "warning"
}}"""
            
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]
            
            response = await llm_factory.generate(messages=messages, temperature=0.2, max_tokens=400)
            
            # Parse JSON response
            try:
                result = json.loads(response.content.strip())
                
                # Convert recovery steps to RecoveryStep objects
                recovery_steps = []
                for step in result.get("recovery_steps", []):
                    recovery_steps.append(RecoveryStep(
                        step_number=step.get("step_number", len(recovery_steps) + 1),
                        instruction=step.get("instruction", ""),
                        ui_element=step.get("ui_element")
                    ))
                
                result["recovery_steps"] = recovery_steps
                return result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM JSON response for error explanation")
                # Fallback to basic explanation
                return {
                    "explanation": response.content.strip()[:200],
                    "cause": "Unknown cause",
                    "recovery_steps": [
                        RecoveryStep(
                            step_number=1,
                            instruction="Try refreshing the page",
                            ui_element="Browser Refresh"
                        )
                    ],
                    "prevention_tip": "Contact support if the error persists",
                    "severity": "warning"
                }
                
        except Exception as e:
            logger.error(f"Error generating error explanation: {e}")
            return {
                "explanation": "An unexpected error occurred.",
                "cause": "Unable to determine the cause",
                "recovery_steps": [
                    RecoveryStep(
                        step_number=1,
                        instruction="Refresh the page and try again",
                        ui_element="Browser Refresh"
                    )
                ],
                "prevention_tip": "Contact technical support if the issue persists",
                "severity": "warning"
            }


# Global guidance service instance
guidance_service = GuidanceService()
