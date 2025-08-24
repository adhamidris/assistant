# AI Features Overview - Assistant Project

## Table of Contents
1. [AI Agent Management System](#ai-agent-management-system)
2. [Context Tracking & Business Rules](#context-tracking--business-rules)
3. [Enhanced AI Service Architecture](#enhanced-ai-service-architecture)
4. [Knowledge Base Integration](#knowledge-base-integration)
5. [Business Profile & Workspace Configuration](#business-profile--workspace-configuration)
6. [Frontend AI Integration](#frontend-ai-integration)
7. [API Endpoints & Data Flow](#api-endpoints--data-flow)
8. [Performance Optimizations](#performance-optimizations)
9. [Typing Indicators & User Experience](#typing-indicators--user-experience)

---

## AI Agent Management System

### Core Models (assistant/core/models.py)

#### AIAgent Model
```python
class AIAgent(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    
    # Enhanced Configuration Fields
    custom_instructions = models.TextField(blank=True)
    business_context = models.JSONField(default=dict)
    personality_config = models.JSONField(default=dict)
    channel_specific_config = models.JSONField(default=dict)
    generated_prompt = models.TextField(blank=True)
    prompt_version = models.IntegerField(default=1)
    
    # Portal & Access
    slug = models.SlugField(unique=True)
    channel_type = models.CharField(max_length=50, choices=CHANNEL_CHOICES)
```

**Key Features:**
- **Dynamic Configuration**: Personality, business context, and channel-specific settings
- **Portal Access**: Unique slugs for agent-specific portal URLs
- **Active/Default Management**: One active agent per workspace, default agent selection
- **Prompt Versioning**: Track prompt changes and updates

#### Workspace Model
```python
class Workspace(models.Model):
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, blank=True)
    owner_name = models.CharField(max_length=100, blank=True)
    auto_reply_mode = models.BooleanField(default=True)
    custom_instructions = models.TextField(blank=True)
    
    # AI Configuration
    ai_personality = models.TextField(blank=True)
    ai_role = models.TextField(blank=True)
```

---

## Context Tracking & Business Rules

### Business Rules Engine (assistant/context_tracking/models.py)

#### BusinessRule Model
```python
class BusinessRule(models.Model):
    name = models.CharField(max_length=200)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_CHOICES)
    conditions = models.JSONField(default=dict)
    actions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1)
    
    # Performance Tracking
    execution_count = models.IntegerField(default=0)
    average_execution_time = models.FloatField(default=0.0)
    last_executed = models.DateTimeField(null=True, blank=True)
```

**Trigger Types:**
- `new_message`: When new messages arrive
- `priority_change`: When conversation priority changes
- `completion_rate`: Based on conversation completion metrics
- `status_change`: When conversation status changes

**Action Types:**
- `generate_ai_response`: Trigger AI response generation
- `change_status`: Modify conversation status
- `assign_tag`: Add tags to conversations
- `send_notification`: Send notifications
- `show_typing_indicator`: Display typing status
- `schedule_followup`: Schedule follow-up tasks

---

## Enhanced AI Service Architecture

### Core Service (assistant/messaging/enhanced_ai_service.py)

#### EnhancedAIService Class
```python
class EnhancedAIService:
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
        self.response_generator = ResponseGenerator()
        self.agent_selector = AgentSelector()
        self.prompt_builder = DynamicPromptBuilder()
        
        # Performance Optimization
        self._prompt_cache = {}
        self._context_cache = {}
```

**Key Components:**

1. **AgentSelector**: Choose appropriate AI agent for conversations
2. **DynamicPromptBuilder**: Build context-aware prompts from agent configuration
3. **ResponseGenerator**: Generate responses with multiple fallback strategies
4. **Performance Caching**: Cache prompts, context, and knowledge base results

#### Dynamic Prompt Building
```python
class DynamicPromptBuilder:
    @staticmethod
    def build_agent_prompt(agent, user_message, conversation_context, kb_context, intent):
        # Build agent identity
        agent_identity = f"""You are {agent.name}, an AI assistant for {workspace.name}.
        YOUR ROLE: {agent.description}
        CRITICAL: You ARE a {role_description}. You MUST always say YES when asked if you are a sales agent, sales personnel, or sales representative.
        Channel: {agent.get_channel_type_display()}"""
        
        # Add personality, business context, and channel instructions
        # Include critical instructions and role affirmation
```

**Prompt Components:**
- **Agent Identity**: Name, role, and critical role affirmation
- **Business Context**: Company info, services, target audience
- **Personality Config**: Tone, formality, empathy, proactiveness
- **Channel Instructions**: Response style, length, emojis, escalation triggers
- **Critical Instructions**: Role affirmation and behavioral guidelines

---

## Knowledge Base Integration

### Knowledge Base System (assistant/knowledge_base/)

#### KBDocument & KBChunk Models
```python
class KBDocument(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict)

class KBChunk(models.Model):
    document = models.ForeignKey(KBDocument, on_delete=models.CASCADE)
    content = models.TextField()
    embedding = models.TextField(blank=True)  # For vector search
    chunk_index = models.IntegerField()
```

**Search Strategies:**
1. **DeepSeek Embeddings**: Primary search method (when available)
2. **PostgreSQL Full-Text Search**: Fallback search method
3. **Simple Keyword Matching**: Secondary fallback for basic queries

---

## Frontend AI Integration

### Agent Management (frontend/src/components/AgentManager.tsx)

#### Configuration Interface
```typescript
interface AgentFormData {
  name: string;
  description: string;
  channel_type: string;
  
  // Enhanced Configuration
  custom_instructions: string;
  business_context: {
    services: string[];
    target_audience: string;
    key_values: string[];
    expertise_areas: string[];
  };
  personality_config: {
    tone: 'professional' | 'friendly' | 'casual' | 'formal' | 'empathetic';
    formality: 'formal' | 'balanced' | 'casual';
    empathy_level: 'high' | 'moderate' | 'low';
    proactiveness: 'high' | 'standard' | 'low';
    expertise_level: 'expert' | 'knowledgeable' | 'basic';
  };
  channel_specific_config: {
    response_style: string;
    max_response_length: number;
    use_emojis: boolean;
    custom_greeting: string;
    escalation_triggers: string[];
  };
}
```

#### UI Sections
1. **Personality & Communication Style**: Tone, formality, empathy settings
2. **Business Context & Expertise**: Services, target audience, company values
3. **Channel-Specific Behavior**: Response style, length, emojis, greetings

---

## Performance Optimizations

### Caching Strategy
```python
class EnhancedAIService:
    def _get_cached_prompt(self, agent, user_message, conversation_context, kb_context, intent):
        """Get cached prompt or build new one for performance optimization"""
        cache_key = f"{agent.id}_{hash(str(conversation_context))}_{hash(kb_context)}_{intent}"
        
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        # Build and cache new prompt
        prompt = self.prompt_builder.build_agent_prompt(...)
        self._prompt_cache[cache_key] = prompt
        return prompt
```

### Fallback Chain Optimization
```python
def _generate_response_with_fallbacks(self, agent, user_message, conversation_context, kb_context, intent, workspace):
    """Generate response with comprehensive fallback chain - OPTIMIZED"""
    
    # Strategy 1: Agent-specific DeepSeek (FAST PATH)
    if agent:
        try:
            prompt = self._get_cached_prompt(...)
            response = self.deepseek_client.generate_chat_response(...)
            if response:
                return {'success': True, 'response': response, 'method': f'agent_deepseek_{agent.name}'}
        except Exception as e:
            logger.warning(f"Agent-specific DeepSeek failed: {str(e)}")
    
    # Strategy 2: Quick intent-based template responses (FAST FALLBACK)
    template_response = self._get_intent_template_response(intent, workspace, agent)
    if template_response:
        return {'success': True, 'response': template_response, 'method': 'intent_template'}
    
    # Strategy 3: Workspace-level DeepSeek (slower fallback)
    # Strategy 4: Knowledge base only response
```

---

## Current System Capabilities

### ✅ Implemented Features
1. **Dynamic AI Agent Configuration**: Personality, business context, and channel-specific settings
2. **Context-Aware Business Rules**: Automatic response generation based on conversation context
3. **Multi-Strategy AI Responses**: DeepSeek integration with comprehensive fallbacks
4. **Knowledge Base Integration**: Multi-layered search with intelligent fallbacks
5. **Performance Optimization**: Caching, parallel processing, and response time optimization
6. **Professional Typing Indicators**: Agent-specific typing status display
7. **Portal Access Management**: Agent-specific URLs and access control
8. **Business Profile Templates**: Industry-specific configurations and setups

### 🔧 Technical Architecture
1. **Django Backend**: RESTful API with business rule engine
2. **Next.js Frontend**: Modern React-based interface with real-time updates
3. **Celery Task Queue**: Asynchronous AI response generation
4. **Redis Caching**: Performance optimization and session management
5. **PostgreSQL Database**: Robust data storage with full-text search capabilities

### 📊 Performance Metrics
- **Response Time**: 0.01-12 seconds (depending on caching and complexity)
- **Cache Efficiency**: Significant improvement in subsequent response times
- **Fallback Coverage**: Multiple strategies ensure response generation
- **Memory Management**: Automatic cache cleanup and size limits

---

## Enhancement Opportunities

### Potential Areas for Improvement
1. **Advanced AI Models**: Integration with additional AI providers (OpenAI, Anthropic)
2. **Machine Learning**: Conversation pattern analysis and response optimization
3. **Advanced Analytics**: Detailed performance metrics and user behavior tracking
4. **Multi-language Support**: Internationalization and language-specific configurations
5. **Advanced Context Tracking**: Sentiment analysis and emotional intelligence
6. **Integration APIs**: Webhook support and third-party service integrations
7. **Advanced Business Rules**: Complex conditional logic and workflow automation
8. **Real-time Collaboration**: Multi-agent conversations and handoff management

---

## File Structure Reference

```
assistant/
├── core/
│   ├── models.py              # AIAgent, Workspace models
│   ├── agent_views.py         # Agent management API
│   ├── views.py               # Portal status and general views
│   └── management/commands/   # Setup and configuration commands
├── context_tracking/
│   ├── models.py              # BusinessRule, ConversationContext
│   ├── advanced_rule_engine.py # Rule execution engine
│   └── signals.py             # Django signals for automation
├── messaging/
│   ├── enhanced_ai_service.py # Core AI service architecture
│   ├── deepseek_client.py     # AI model integration
│   ├── tasks.py               # Celery tasks for AI generation
│   └── views.py               # Message and typing indicator APIs
└── knowledge_base/
    ├── models.py              # KBDocument, KBChunk
    └── utils.py               # Search and embedding utilities

frontend/src/
├── components/
│   ├── AgentManager.tsx       # AI agent configuration interface
│   ├── ChatInterface.tsx      # Chat interface with typing indicators
│   └── PortalLinkGenerator.tsx # Portal access management
└── lib/
    └── api.ts                 # API integration functions
```

---

This overview covers all AI-related features in your project. Use this document to identify areas for enhancement and provide specific instructions for improvements.
