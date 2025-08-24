import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from .models import ContextCase, CaseTypeConfiguration, CaseMatchingRule
from .duplicate_detector import DuplicateDetector

logger = logging.getLogger(__name__)

class CaseAnalyzer:
    """AI-powered case analysis engine for intelligent case management"""
    
    def __init__(self, workspace, ai_service):
        self.workspace = workspace
        self.ai_service = ai_service
        self.duplicate_detector = DuplicateDetector(workspace)
        
    def analyze_message_for_cases(self, message: str, conversation_context: List[Dict], agent) -> Dict[str, Any]:
        """
        Analyze incoming message for case creation or updates
        
        Returns:
            {
                "action": "create"|"update"|"none",
                "case_data": {...},
                "matching_cases": [...],
                "confidence": float,
                "reasoning": str
            }
        """
        try:
            # Step 1: Check for existing case matches
            potential_matches = self._find_matching_cases(message, conversation_context)
            
            if potential_matches:
                # Analyze for updates
                update_analysis = self._analyze_for_updates(message, potential_matches, agent)
                if update_analysis["should_update"]:
                    return {
                        "action": "update",
                        "case_data": update_analysis["updates"],
                        "matching_cases": potential_matches,
                        "confidence": update_analysis["confidence"],
                        "reasoning": update_analysis["reasoning"]
                    }
            
            # Step 2: Check for new case creation
            creation_analysis = self._analyze_for_creation(message, conversation_context, agent)
            if creation_analysis["should_create"]:
                return {
                    "action": "create",
                    "case_data": creation_analysis["case_data"],
                    "matching_cases": [],
                    "confidence": creation_analysis["confidence"],
                    "reasoning": creation_analysis["reasoning"]
                }
                
            return {
                "action": "none", 
                "case_data": {}, 
                "matching_cases": [], 
                "confidence": 0.0,
                "reasoning": "Message does not contain actionable business data"
            }
            
        except Exception as e:
            logger.error(f"Case analysis failed: {str(e)}")
            return {
                "action": "error",
                "case_data": {},
                "matching_cases": [],
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}"
            }
    
    def _find_matching_cases(self, message: str, conversation_context: List[Dict]) -> List[Dict]:
        """Find existing cases that might match the current message"""
        try:
            # Get active case types for this workspace
            case_types = CaseTypeConfiguration.objects.filter(
                workspace=self.workspace,
                is_active=True
            ).values_list("case_type", flat=True)
            
            if not case_types:
                return []
            
            # Get existing open cases
            existing_cases = ContextCase.objects.filter(
                workspace=self.workspace,
                status__in=["open", "in_progress", "pending"],
                case_type__in=case_types
            ).select_related("assigned_agent")
            
            matching_cases = []
            
            for case in existing_cases:
                # Get matching rules for this case type
                matching_rules = CaseMatchingRule.objects.filter(
                    workspace=self.workspace,
                    case_type=case.case_type,
                    is_active=True
                ).order_by("-priority")
                
                for rule in matching_rules:
                    # Calculate matching score
                    score = rule.get_matching_score(
                        self._extract_message_data(message, conversation_context),
                        case
                    )
                    
                    if score >= rule.similarity_threshold:
                        matching_cases.append({
                            "case": case,
                            "rule": rule,
                            "score": score,
                            "action": rule.action_on_match
                        })
                        break  # Use highest priority rule only
            
            # Sort by score and return top matches
            matching_cases.sort(key=lambda x: x["score"], reverse=True)
            return matching_cases[:5]  # Limit to top 5 matches
            
        except Exception as e:
            logger.error(f"Error finding matching cases: {str(e)}")
            return []
    
    def _analyze_for_updates(self, message: str, matching_cases: List[Dict], agent) -> Dict[str, Any]:
        """Analyze if message should update existing cases"""
        try:
            # Get the best match
            best_match = matching_cases[0] if matching_cases else None
            if not best_match:
                return {"should_update": False, "confidence": 0.0}
            
            case = best_match["case"]
            rule = best_match["rule"]
            
            # Use AI to determine if update is needed
            update_params = getattr(agent, "case_update_parameters", {})
            
            analysis_prompt = f"""
            Analyze if this message requires updating the existing case:
            
            MESSAGE: {message}
            EXISTING CASE DATA: {json.dumps(case.extracted_data, indent=2)}
            CASE TYPE: {case.case_type}
            CURRENT STATUS: {case.status}
            UPDATE PARAMETERS: {json.dumps(update_params, indent=2)}
            
            Determine:
            1. Should this case be updated? (yes/no)
            2. What specific parameters need updating?
            3. What are the new values?
            4. Should the status change?
            5. Confidence level (0-1)
            
            Respond in JSON format:
            {{
                "should_update": boolean,
                "updates": {{"parameter": "new_value"}},
                "status_change": "new_status" or null,
                "confidence": float,
                "reasoning": "explanation"
            }}
            """
            
            try:
                ai_response = self.ai_service.analyze_with_deepseek(analysis_prompt)
                update_decision = json.loads(ai_response)
                
                if update_decision.get("should_update") and update_decision.get("confidence", 0) > 0.7:
                    return {
                        "should_update": True,
                        "updates": update_decision.get("updates", {}),
                        "status_change": update_decision.get("status_change"),
                        "confidence": update_decision.get("confidence", 0.8),
                        "reasoning": update_decision.get("reasoning", "AI analysis indicates update needed")
                    }
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"AI update analysis failed: {str(e)}")
                
                # Fallback to rule-based update logic
                return self._fallback_update_analysis(message, case, rule)
                
        except Exception as e:
            logger.error(f"Update analysis failed: {str(e)}")
            
        return {"should_update": False, "confidence": 0.0}
    
    def _fallback_update_analysis(self, message: str, case: ContextCase, rule: CaseMatchingRule) -> Dict[str, Any]:
        """Fallback update analysis when AI fails"""
        try:
            # Simple keyword-based update detection
            message_lower = message.lower()
            case_data = case.extracted_data
            
            updates = {}
            status_change = None
            
            # Check for status-related keywords
            if any(word in message_lower for word in ["complete", "finished", "done", "resolved"]):
                status_change = "closed"
            elif any(word in message_lower for word in ["progress", "working", "processing"]):
                status_change = "in_progress"
            elif any(word in message_lower for word in ["waiting", "pending", "hold"]):
                status_change = "pending"
            
            # Check for data updates based on case type
            if case.case_type == "sales_lead":
                if "email" in message_lower and "@" in message:
                    # Extract email
                    import re
                    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{{2,}}\b", message)
                    if email_match:
                        updates["email"] = email_match.group()
                
                if "phone" in message_lower:
                    # Extract phone
                    phone_match = re.search(r"\b\d{{3}}[-.]?\d{{3}}[-.]?\d{{4}}\b", message)
                    if phone_match:
                        updates["phone"] = phone_match.group()
            
            # If we have updates or status change, consider it an update
            if updates or status_change:
                return {
                    "should_update": True,
                    "updates": updates,
                    "status_change": status_change,
                    "confidence": 0.6,
                    "reasoning": "Rule-based analysis detected potential updates"
                }
                
        except Exception as e:
            logger.error(f"Fallback update analysis failed: {str(e)}")
            
        return {"should_update": False, "confidence": 0.0}
    
    def _analyze_for_creation(self, message: str, conversation_context: List[Dict], agent) -> Dict[str, Any]:
        """Analyze if message should create a new case"""
        try:
            # Get case type configurations
            case_configs = CaseTypeConfiguration.objects.filter(
                workspace=self.workspace,
                is_active=True,
                auto_creation_enabled=True
            )
            
            if not case_configs:
                return {"should_create": False, "confidence": 0.0}
            
            # Use AI to determine case creation
            creation_prompt = f"""
            Analyze if this message should create a new case:
            
            MESSAGE: {message}
            CONVERSATION CONTEXT: {json.dumps(conversation_context, indent=2)}
            SUPPORTED CASE TYPES: {[config.case_type for config in case_configs]}
            
            Determine:
            1. Should a new case be created? (yes/no)
            2. What type of case?
            3. Extract all relevant data according to the case type
            4. Confidence level (0-1)
            
            Respond in JSON format:
            {{
                "should_create": boolean,
                "case_type": "string",
                "case_data": {{"extracted data"}},
                "confidence": float,
                "reasoning": "explanation"
            }}
            """
            
            try:
                ai_response = self.ai_service.analyze_with_deepseek(creation_prompt)
                creation_decision = json.loads(ai_response)
                
                if creation_decision.get("should_create") and creation_decision.get("confidence", 0) > 0.7:
                    # Validate the case type
                    case_type = creation_decision.get("case_type")
                    if case_type in [config.case_type for config in case_configs]:
                        return creation_decision
                        
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"AI creation analysis failed: {str(e)}")
                
                # Fallback to rule-based creation logic
                return self._fallback_creation_analysis(message, case_configs)
                
        except Exception as e:
            logger.error(f"Creation analysis failed: {str(e)}")
            
        return {"should_create": False, "confidence": 0.0}
    
    def _fallback_creation_analysis(self, message: str, case_configs: List[CaseTypeConfiguration]) -> Dict[str, Any]:
        """Fallback creation analysis when AI fails"""
        try:
            message_lower = message.lower()
            
            # Simple keyword-based case type detection
            case_type_mapping = {
                "sales_lead": ["lead", "inquiry", "quote", "proposal", "interest", "buy", "purchase"],
                "support_ticket": ["help", "issue", "problem", "error", "bug", "support", "assist"],
                "booking_request": ["book", "schedule", "appointment", "reservation", "meeting"],
                "order_inquiry": ["order", "track", "status", "delivery", "shipping"]
            }
            
            detected_case_type = None
            confidence = 0.0
            
            for case_type, keywords in case_type_mapping.items():
                keyword_matches = sum(1 for keyword in keywords if keyword in message_lower)
                if keyword_matches > 0:
                    case_confidence = min(0.5 + (keyword_matches * 0.1), 0.8)
                    if case_confidence > confidence:
                        detected_case_type = case_type
                        confidence = case_confidence
            
            if detected_case_type:
                # Extract basic data
                extracted_data = self._extract_basic_data(message, detected_case_type)
                
                return {
                    "should_create": True,
                    "case_type": detected_case_type,
                    "case_data": extracted_data,
                    "confidence": confidence,
                    "reasoning": f"Rule-based analysis detected {detected_case_type} case"
                }
                
        except Exception as e:
            logger.error(f"Fallback creation analysis failed: {str(e)}")
            
        return {"should_create": False, "confidence": 0.0}
    
    def _extract_basic_data(self, message: str, case_type: str) -> Dict[str, Any]:
        """Extract basic data from message for case creation"""
        import re
        
        extracted_data = {
            "source_message": message,
            "detection_method": "rule_based"
        }
        
        # Extract common fields
        # Email
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{{2,}}\b", message)
        if email_match:
            extracted_data["email"] = email_match.group()
        
        # Phone
        phone_match = re.search(r"\b\d{{3}}[-.]?\d{{3}}[-.]?\d{{4}}\b", message)
        if phone_match:
            extracted_data["phone"] = phone_match.group()
        
        # Name (simple pattern)
        name_patterns = [
            r"my name is (\w+)",
            r"i am (\w+)",
            r"this is (\w+)",
            r"(\w+) here"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, message, re.IGNORECASE)
            if name_match:
                extracted_data["name"] = name_match.group(1)
                break
        
        # Case type specific extraction
        if case_type == "sales_lead":
            if "company" in message.lower():
                extracted_data["company"] = "Company mentioned"
            if any(word in message.lower() for word in ["budget", "price", "cost"]):
                extracted_data["budget_mentioned"] = True
                
        elif case_type == "support_ticket":
            if any(word in message.lower() for word in ["urgent", "critical", "emergency"]):
                extracted_data["priority"] = "high"
            if any(word in message.lower() for word in ["software", "app", "system"]):
                extracted_data["category"] = "technical"
                
        elif case_type == "booking_request":
            # Extract date/time patterns
            date_patterns = [
                r"(\d{{1,2}})[/-](\d{{1,2}})[/-](\d{{2,4}})",  # MM/DD/YYYY
                r"(\w+ \d{{1,2}},? \d{{4}})",  # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, message)
                if date_match:
                    extracted_data["preferred_date"] = date_match.group()
                    break
        
        return extracted_data
    
    def _extract_message_data(self, message: str, conversation_context: List[Dict]) -> Dict[str, Any]:
        """Extract structured data from message and conversation context"""
        data = {
            "message_content": message,
            "message_length": len(message),
            "has_question": "?" in message,
            "has_urgency": any(word in message.lower() for word in ["urgent", "asap", "immediately", "now"]),
            "conversation_length": len(conversation_context)
        }
        
        # Extract from conversation context
        if conversation_context:
            # Get customer identifier if available
            for ctx in conversation_context:
                if ctx.get("role") == "user":
                    # Look for contact info in user messages
                    if "email" in ctx.get("content", "").lower():
                        data["customer_email"] = True
                    if "phone" in ctx.get("content", "").lower():
                        data["customer_phone"] = True
        
        return data
    
    def get_case_creation_probability(self, message: str, case_type: str) -> float:
        """Calculate probability that a message should create a case of given type"""
        try:
            # This could be enhanced with ML models in the future
            message_lower = message.lower()
            
            # Base probability
            base_prob = 0.1
            
            # Case type specific keywords
            type_keywords = {
                "sales_lead": ["lead", "inquiry", "quote", "interest", "buy"],
                "support_ticket": ["help", "issue", "problem", "error", "support"],
                "booking_request": ["book", "schedule", "appointment", "reservation"],
                "order_inquiry": ["order", "track", "status", "delivery"]
            }
            
            keywords = type_keywords.get(case_type, [])
            keyword_matches = sum(1 for keyword in keywords if keyword in message_lower)
            
            # Increase probability based on keyword matches
            keyword_boost = min(keyword_matches * 0.2, 0.6)
            
            # Increase probability for longer messages (more context)
            length_boost = min(len(message) / 1000, 0.2)
            
            # Increase probability for questions
            question_boost = 0.1 if "?" in message else 0
            
            total_prob = base_prob + keyword_boost + length_boost + question_boost
            
            return min(total_prob, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating case creation probability: {str(e)}")
            return 0.0
