from celery import shared_task
from django.conf import settings
from django.utils import timezone
import requests
import os
import tempfile
import logging

from .models import Message, AudioTranscription, MessageDraft
from core.models import Conversation
from .ai_utils import openai_client, response_generator, conversation_analyzer
from notifications.services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_audio_message(self, message_id):
    """
    Process audio message: download, transcribe, and create text message
    """
    try:
        message = Message.objects.get(id=message_id)
        
        if message.message_type != 'audio':
            logger.error(f"Message {message_id} is not an audio message")
            return
        
        # Update status
        message.status = 'processing'
        message.save()
        
        # Download audio file
        audio_response = requests.get(message.media_url)
        audio_response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(audio_response.content)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe with OpenAI Whisper
            transcript_result = openai_client.transcribe_audio(temp_file_path)
            
            if not transcript_result['success']:
                raise Exception(transcript_result.get('error', 'Transcription failed'))
            
            # Create transcription record
            transcription = AudioTranscription.objects.create(
                message=message,
                transcribed_text=transcript_result['text'],
                language=transcript_result.get('language'),
                duration=transcript_result.get('duration'),
                confidence=transcript_result.get('confidence')
            )
            
            # Update message with transcribed text
            message.text = f"Audio: {transcript_result['text']}"
            message.status = 'processed'
            message.save()
            
            # Create a synthetic text message for the transcription
            text_message = Message.objects.create(
                conversation=message.conversation,
                sender=message.sender,
                message_type='text',
                text=transcript_result['text'],
                status='sent'
            )
            
            # Trigger AI response if from client and auto-reply enabled
            if (message.sender == 'client' and 
                message.conversation.workspace.auto_reply_mode):
                generate_ai_response.delay(str(text_message.id))
            
            logger.info(f"Successfully transcribed audio message {message_id}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
        
    except Exception as exc:
        logger.error(f"Error processing audio message {message_id}: {str(exc)}")
        
        # Update message status
        try:
            message = Message.objects.get(id=message_id)
            message.status = 'failed'
            message.save()
        except Message.DoesNotExist:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc


@shared_task(bind=True, max_retries=3)
def generate_ai_response(self, message_id, force_generation=False):
    """
    Generate AI response using DeepSeek and knowledge base
    """
    try:
        print(f"🤖 Generating AI response for message: {message_id}")
        message = Message.objects.select_related(
            'conversation', 'conversation__workspace'
        ).get(id=message_id)
        
        conversation = message.conversation
        workspace = conversation.workspace
        
        # Skip if not in auto-reply mode and not forced
        if not workspace.auto_reply_mode and not force_generation:
            print(f"⏭️ Skipping AI response for message {message_id} - auto-reply disabled")
            logger.info(f"Skipping AI response for message {message_id} - auto-reply disabled")
            return
        
        print(f"✅ Auto-reply enabled for workspace: {workspace.name}")
        
        # Get conversation history for context
        recent_messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).order_by('-created_at')[:10]
        
        # Convert to format expected by response generator
        context_messages = []
        for msg in reversed(recent_messages):
            context_messages.append({
                'sender': msg.sender,
                'text': msg.text,
                'message_type': msg.message_type
            })
        
        # Build conversation context
        conversation_context = response_generator.build_conversation_context(context_messages)
        
        # Search knowledge base for relevant context
        kb_context = ""
        try:
            from knowledge_base.utils import search_knowledge_base
            kb_results = search_knowledge_base(message.text, workspace.id, limit=3)
            if kb_results:
                kb_context = "\n\nRelevant information from knowledge base:\n"
                kb_context += "\n".join([result['text'] for result in kb_results])
        except Exception as e:
            logger.warning(f"Knowledge base search failed: {str(e)}")
        
        # Classify intent
        intent, confidence = openai_client.classify_intent(message.text)
        
        # Generate response using DeepSeek
        response_result = response_generator.generate_response(
            user_message=message.text,
            conversation_context=conversation_context,
            workspace=workspace,  # Pass workspace object
            kb_context=kb_context,
            intent=intent
        )
        
        # Extract response text
        if isinstance(response_result, dict):
            if not response_result.get('success', True):
                raise Exception(response_result.get('error', 'Response generation failed'))
            ai_response_text = response_result.get('text', 'Sorry, I could not generate a response.')
        else:
            ai_response_text = str(response_result)
        
        # Update message intent classification
        message.intent_classification = intent
        message.confidence_score = confidence
        message.save()
        
        # Create response based on workspace mode
        if workspace.auto_reply_mode:
            # Send response immediately
            response_message = Message.objects.create(
                conversation=conversation,
                sender='assistant',
                message_type='text',
                text=ai_response_text,
                status='sent',
                confidence_score=confidence
            )
            
            print(f"✅ Created AI response: {ai_response_text[:100]}...")
            logger.info(f"Sent automatic AI response for message {message_id}")
            
            # Send notification to business owner about new message
            try:
                workspace_owner = workspace.owner
                if workspace_owner:
                    NotificationService.send_new_message_notification(
                        user=workspace_owner,
                        conversation=conversation,
                        message=message
                    )
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
        
            # Check if AI response indicates appointment booking
            if intent == 'appointment' or any(word in ai_response_text.lower() for word in ['booked', 'scheduled', 'confirmed']):
                try:
                    from .appointment_handler import appointment_handler
                    appointment = appointment_handler.create_appointment_from_ai_response(
                        conversation=conversation,
                        ai_response_text=ai_response_text,
                        original_message=message.text
                    )
                    if appointment:
                        print(f"📅 Created appointment: {appointment.title} at {appointment.start_time}")
                        
                        # Send appointment booking notification
                        try:
                            workspace_owner = workspace.owner
                            if workspace_owner:
                                NotificationService.send_appointment_booking_notification(
                                    user=workspace_owner,
                                    appointment=appointment
                                )
                        except Exception as e:
                            logger.error(f"Failed to send appointment notification: {str(e)}")
                        
                        # Add appointment confirmation to AI response
                        confirmation_message = Message.objects.create(
                            conversation=conversation,
                            sender='assistant',
                            message_type='system',
                            text=f"✅ Appointment confirmed: {appointment.title} on {appointment.start_time.strftime('%A, %B %d at %I:%M %p')}",
                            status='sent'
                        )
                except Exception as e:
                    logger.error(f"Failed to handle appointment booking: {str(e)}")
            
        else:
            # Create draft for approval
            draft = MessageDraft.objects.create(
                conversation=conversation,
                suggested_text=ai_response_text,
                confidence_score=confidence,
                context_sources=[]  # Add KB chunk IDs if available
            )
            
            logger.info(f"Created draft response for message {message_id}")
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
        
    except Exception as exc:
        logger.error(f"Error generating AI response for message {message_id}: {str(exc)}")
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc


# Intent classification is now handled in ai_utils.py


@shared_task
def cleanup_old_sessions():
    """
    Clean up old inactive sessions (runs daily)
    """
    from datetime import timedelta
    from django.utils import timezone
    from core.models import Session
    
    cutoff_date = timezone.now() - timedelta(days=7)
    
    # Deactivate old sessions
    old_sessions = Session.objects.filter(
        last_seen_at__lt=cutoff_date,
        is_active=True
    )
    
    count = old_sessions.update(is_active=False)
    logger.info(f"Deactivated {count} old sessions")
    
    return count


@shared_task
def cleanup_old_drafts():
    """
    Clean up old unprocessed drafts (runs daily)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=3)
    
    # Delete old unprocessed drafts
    old_drafts = MessageDraft.objects.filter(
        created_at__lt=cutoff_date,
        is_approved=False,
        is_rejected=False
    )
    
    count = old_drafts.count()
    old_drafts.delete()
    
    logger.info(f"Deleted {count} old unprocessed drafts")
    
    return count


@shared_task(bind=True, max_retries=2)
def analyze_conversation_sentiment(self, conversation_id):
    """
    Analyze sentiment of a conversation and update metadata
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Get conversation messages
        messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).order_by('created_at')
        
        if not messages.exists():
            logger.info(f"No messages found for conversation {conversation_id}")
            return
        
        # Format messages for analysis
        message_data = []
        for msg in messages:
            message_data.append({
                'sender': msg.sender,
                'text': msg.text,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat()
            })
        
        # Analyze sentiment
        conversation_text = conversation_analyzer._format_messages_for_analysis(message_data)
        sentiment_result = conversation_analyzer.analyze_sentiment(conversation_text)
        
        if sentiment_result.get('success'):
            # Update conversation with sentiment data
            conversation.sentiment_score = sentiment_result.get('satisfaction_level', 3)
            conversation.sentiment_data = sentiment_result
            conversation.save()
            
            logger.info(f"Updated sentiment for conversation {conversation_id}: {sentiment_result.get('overall_sentiment')}")
        else:
            logger.error(f"Sentiment analysis failed for conversation {conversation_id}: {sentiment_result.get('error')}")
            
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for sentiment analysis")
    except Exception as e:
        logger.error(f"Sentiment analysis task failed for conversation {conversation_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=2)
def generate_conversation_summary(self, conversation_id):
    """
    Generate a summary of a conversation
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Get conversation messages
        messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).order_by('created_at')
        
        if not messages.exists():
            logger.info(f"No messages found for conversation {conversation_id}")
            return
        
        # Format messages for analysis
        message_data = []
        for msg in messages:
            message_data.append({
                'sender': msg.sender,
                'text': msg.text,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat()
            })
        
        # Generate summary
        summary_result = conversation_analyzer.summarize_conversation(message_data)
        
        if summary_result.get('success'):
            # Update conversation with summary
            conversation.summary = summary_result.get('summary', '')
            conversation.key_points = summary_result.get('key_points', [])
            conversation.resolution_status = summary_result.get('resolution_status', 'pending')
            conversation.action_items = summary_result.get('action_items', [])
            conversation.save()
            
            logger.info(f"Generated summary for conversation {conversation_id}")
        else:
            logger.error(f"Summary generation failed for conversation {conversation_id}: {summary_result.get('error')}")
            
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for summary generation")
    except Exception as e:
        logger.error(f"Summary generation task failed for conversation {conversation_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=2)
def extract_conversation_entities(self, conversation_id):
    """
    Extract entities from a conversation
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Get conversation messages
        messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).order_by('created_at')
        
        if not messages.exists():
            logger.info(f"No messages found for conversation {conversation_id}")
            return
        
        # Format messages for analysis
        message_data = []
        for msg in messages:
            message_data.append({
                'sender': msg.sender,
                'text': msg.text,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat()
            })
        
        # Extract entities
        conversation_text = conversation_analyzer._format_messages_for_analysis(message_data)
        entities_result = conversation_analyzer.extract_entities(conversation_text)
        
        if entities_result.get('success'):
            # Update conversation with extracted entities
            conversation.extracted_entities = entities_result
            conversation.save()
            
            logger.info(f"Extracted entities for conversation {conversation_id}")
        else:
            logger.error(f"Entity extraction failed for conversation {conversation_id}: {entities_result.get('error')}")
            
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for entity extraction")
    except Exception as e:
        logger.error(f"Entity extraction task failed for conversation {conversation_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=2)
def generate_comprehensive_insights(self, conversation_id):
    """
    Generate comprehensive insights for a conversation (summary + sentiment + entities)
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Get conversation messages
        messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).order_by('created_at')
        
        if not messages.exists():
            logger.info(f"No messages found for conversation {conversation_id}")
            return
        
        # Format messages for analysis
        message_data = []
        for msg in messages:
            message_data.append({
                'sender': msg.sender,
                'text': msg.text,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat()
            })
        
        # Generate comprehensive insights
        insights_result = conversation_analyzer.generate_conversation_insights(message_data)
        
        if insights_result.get('success'):
            # Update conversation with all insights
            summary_data = insights_result.get('summary', {})
            sentiment_data = insights_result.get('sentiment', {})
            entities_data = insights_result.get('entities', {})
            metrics_data = insights_result.get('metrics', {})
            
            conversation.summary = summary_data.get('summary', '')
            conversation.key_points = summary_data.get('key_points', [])
            conversation.resolution_status = summary_data.get('resolution_status', 'pending')
            conversation.action_items = summary_data.get('action_items', [])
            conversation.sentiment_score = sentiment_data.get('satisfaction_level', 3)
            conversation.sentiment_data = sentiment_data
            conversation.extracted_entities = entities_data
            conversation.conversation_metrics = metrics_data
            conversation.insights_generated_at = timezone.now()
            conversation.save()
            
            logger.info(f"Generated comprehensive insights for conversation {conversation_id}")
            return insights_result
        else:
            logger.error(f"Insights generation failed for conversation {conversation_id}: {insights_result.get('error')}")
            
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for insights generation")
    except Exception as e:
        logger.error(f"Insights generation task failed for conversation {conversation_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
