import json
import logging
import time
from typing import Dict, Any, List, Optional, Generator
from .enhanced_ai_service import EnhancedAIService

logger = logging.getLogger(__name__)

class ProgressiveResponder:
    """Progressive response system for conversational AI flow"""
    
    def __init__(self, ai_service: EnhancedAIService):
        self.ai_service = ai_service
        self.response_stages = [
            "acknowledgment",
            "processing_indication", 
            "knowledge_search",
            "case_analysis",
            "final_response"
        ]
    
    def handle_complex_query(self, user_message: str, agent, conversation_context: List[Dict], 
                           requires_kb: bool = False, requires_case_analysis: bool = False) -> Generator[Dict[str, Any], None, None]:
        """Handle complex queries with progressive responses"""
        
        try:
            # Stage 1: Immediate acknowledgment
            acknowledgment = self._generate_acknowledgment(user_message, agent)
            yield {
                "stage": "acknowledgment",
                "response": acknowledgment,
                "show_typing": True,
                "status": "processing"
            }
            
            # Stage 2: Processing indication
            if requires_kb or requires_case_analysis:
                processing_msg = self._generate_processing_message(user_message, requires_kb, requires_case_analysis)
                yield {
                    "stage": "processing_indication",
                    "response": processing_msg,
                    "show_typing": True,
                    "status": "checking_knowledge" if requires_kb else "analyzing_cases"
                }
            
            # Stage 3: Knowledge base search (if needed)
            kb_context = ""
            if requires_kb:
                kb_search_msg = "Let me check our knowledge base for the most accurate information..."
                yield {
                    "stage": "knowledge_search",
                    "response": kb_search_msg,
                    "show_typing": True,
                    "status": "searching_knowledge"
                }
                
                # Perform knowledge base search with callback
                def kb_callback(message):
                    return {
                        "stage": "knowledge_progress",
                        "response": message,
                        "show_typing": True,
                        "status": "searching_knowledge"
                    }
                
                kb_service = self.ai_service._get_knowledge_base_context(user_message, agent.workspace.id)
                kb_context = kb_service
                
                if kb_context:
                    kb_found_msg = "Great! I found relevant information. Let me analyze it for you..."
                else:
                    kb_found_msg = "I have checked our knowledge base. Let me provide the best response I can..."
                    
                yield {
                    "stage": "knowledge_found",
                    "response": kb_found_msg,
                    "show_typing": True,
                    "status": "processing_knowledge"
                }
            
            # Stage 4: Case analysis (if needed)
            case_context = {}
            if requires_case_analysis:
                case_msg = "Now let me check if this relates to any existing cases..."
                yield {
                    "stage": "case_analysis",
                    "response": case_msg,
                    "show_typing": True,
                    "status": "analyzing_cases"
                }
                
                # Perform case analysis
                try:
                    from ..context_tracking.case_service import CaseManagementService
                    case_service = CaseManagementService(agent.workspace)
                    case_service.set_ai_service(self.ai_service)
                    case_result = case_service.process_message_for_cases(user_message, conversation_context, agent)
                    case_context = case_result
                    
                    if case_result["action"] != "none":
                        case_update_msg = f"I have {case_result[action].replace(_,  )}. Preparing your complete response..."
                    else:
                        case_update_msg = "No case updates needed. Finalizing your response..."
                        
                    yield {
                        "stage": "case_processed",
                        "response": case_update_msg,
                        "show_typing": True,
                        "status": "finalizing"
                    }
                except Exception as e:
                    logger.warning(f"Case analysis failed: {str(e)}")
                    case_context = {"action": "none", "error": str(e)}
            
            # Stage 5: Final comprehensive response
            final_response = self._generate_final_response(
                user_message, agent, conversation_context, kb_context, case_context
            )
            
            yield {
                "stage": "final_response",
                "response": final_response,
                "show_typing": False,
                "status": "complete",
                "case_data": case_context if case_context.get("action") != "none" else None
            }
            
        except Exception as e:
            logger.error(f"Progressive response generation failed: {str(e)}")
            error_response = {
                "stage": "error",
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "show_typing": False,
                "status": "error",
                "error": str(e)
            }
            yield error_response
    
    def _generate_acknowledgment(self, user_message: str, agent) -> str:
        """Generate appropriate acknowledgment based on message type"""
        acknowledgment_templates = {
            "question": [
                "I understand your question. Let me look into this for you...",
                "Got it! I will find the best answer for you...",
                "That is a great question. Give me a moment to check everything..."
            ],
            "request": [
                "I will help you with that right away...",
                "Absolutely! Let me take care of this for you...",
                "I am on it! Processing your request now..."
            ],
            "problem": [
                "I see the issue you are facing. Let me investigate this...",
                "I understand the problem. Let me find the best solution...",
                "No worries, I will help resolve this for you..."
            ],
            "default": [
                "Thank you for your message. Let me process this for you...",
                "I have got your message. Give me just a moment...",
                "Understood! Let me take care of this..."
            ]
        }
        
        # Simple intent detection for acknowledgment
        message_lower = user_message.lower()
        if any(word in message_lower for word in ["?", "how", "what", "when", "where", "why"]):
            intent = "question"
        elif any(word in message_lower for word in ["please", "can you", "could you", "need", "want"]):
            intent = "request"
        elif any(word in message_lower for word in ["problem", "issue", "error", "help", "wrong"]):
            intent = "problem"
        else:
            intent = "default"
        
        import random
        return random.choice(acknowledgment_templates[intent])
    
    def _generate_processing_message(self, user_message: str, requires_kb: bool, requires_case_analysis: bool) -> str:
        """Generate processing indication message"""
        if requires_kb and requires_case_analysis:
            return "I will need to check our knowledge base and review any related cases to give you the most complete answer..."
        elif requires_kb:
            return "Let me search our knowledge base to provide you with the most accurate information..."
        elif requires_case_analysis:
            return "I am checking if this relates to any existing cases or if we need to create a new one..."
        else:
            return "Processing your request..."
    
    def _should_use_progressive_response(self, user_message: str, conversation_context: List[Dict]) -> bool:
        """Determine if progressive response is needed"""
        # Check for complexity indicators
        complexity_indicators = [
            len(user_message) > 100,  # Long messages
            "?" in user_message and len(user_message.split()) > 10,  # Complex questions
            any(word in user_message.lower() for word in [
                "explain", "detail", "comprehensive", "complete", "thorough",
                "analyze", "review", "check", "investigate"
            ])
        ]
        
        return any(complexity_indicators)
    
    def _generate_final_response(self, user_message: str, agent, conversation_context: List[Dict], 
                               kb_context: str, case_context: Dict[str, Any]) -> str:
        """Generate the final comprehensive response"""
        try:
            # Build context for final response
            response_context = {
                "kb_found": bool(kb_context),
                "case_action": case_context.get("action", "none") if case_context else "none",
                "case_data": case_context.get("case_data") if case_context else None
            }
            
            # Build enhanced prompt for final response
            final_prompt = f"""
            Based on the analysis completed, provide a comprehensive response to the user message.
            
            USER MESSAGE: {user_message}
            CONVERSATION CONTEXT: {conversation_context}
            KNOWLEDGE BASE CONTEXT: {kb_context or "No specific knowledge base information found"}
            CASE CONTEXT: {json.dumps(case_context, indent=2) if case_context else "No case action taken"}
            
            RESPONSE REQUIREMENTS:
            1. Address the user original question/request directly
            2. Include relevant information from knowledge base if found
            3. Mention any case actions taken (creation, updates) naturally
            4. Maintain the agent personality and tone: {getattr(agent, personality_config, {})}
            5. Follow channel-specific guidelines: {getattr(agent, channel_specific_config, {})}
            
            Provide a natural, helpful response that incorporates all available context.
            """
            
            try:
                response = self.ai_service.deepseek_client.generate_chat_response(
                    messages=[{"role": "user", "content": final_prompt}],
                    system_prompt="You are a helpful AI assistant providing comprehensive responses.",
                    max_tokens=1000
                )
                return response
            except Exception as e:
                logger.error(f"AI response generation failed: {e}")
                return "I apologize, but I encountered an issue while processing your request. Please try again."
                
        except Exception as e:
            logger.error(f"Final response generation failed: {e}")
            return "I apologize, but I encountered an issue while processing your request. Please try again."
    
    def get_response_timing_estimate(self, user_message: str, requires_kb: bool, requires_case_analysis: bool) -> Dict[str, Any]:
        """Estimate timing for progressive response stages"""
        base_time = 0.5  # Base acknowledgment time
        
        timing_estimate = {
            "acknowledgment": base_time,
            "processing_indication": base_time,
            "total_estimated_time": base_time * 2
        }
        
        if requires_kb:
            timing_estimate["knowledge_search"] = 2.0
            timing_estimate["total_estimated_time"] += 2.0
            
        if requires_case_analysis:
            timing_estimate["case_analysis"] = 1.5
            timing_estimate["total_estimated_time"] += 1.5
            
        timing_estimate["final_response"] = 1.0
        timing_estimate["total_estimated_time"] += 1.0
        
        return timing_estimate
