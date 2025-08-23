from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import BusinessTypeTemplate
import uuid


class Command(BaseCommand):
    help = 'Set up comprehensive industry-specific business templates'

    def handle(self, *args, **options):
        self.stdout.write('Setting up comprehensive business templates...')
        
        # Get or create admin user for template ownership
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('✅ Created admin user for templates')
        
        # Healthcare Template
        healthcare_template, created = BusinessTypeTemplate.objects.get_or_create(
            name='Medical Practice Assistant',
            industry='healthcare',
            defaults={
                'description': 'Complete solution for medical practices including patient management, appointment scheduling, and medical inquiry handling',
                'default_schema_templates': {
                    'patient_management': {
                        'name': 'Patient Management Schema',
                        'description': 'Track patient information, medical history, and appointment details',
                        'fields': [
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'patient_id',
                                'type': 'text',
                                'label': 'Patient ID',
                                'required': True,
                                'validation': {'pattern': '^[A-Z]{2}\\d{6}$'}
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'medical_history',
                                'type': 'textarea',
                                'label': 'Medical History',
                                'required': False
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'allergies',
                                'type': 'tags',
                                'label': 'Allergies',
                                'required': False
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'insurance_provider',
                                'type': 'choice',
                                'label': 'Insurance Provider',
                                'required': True,
                                'choices': ['Blue Cross', 'Aetna', 'Cigna', 'UnitedHealth', 'Other']
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'appointment_status',
                                'type': 'status',
                                'label': 'Appointment Status',
                                'required': True,
                                'choices': ['scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled']
                            }
                        ],
                        'status_workflow': {
                            'default_status': 'scheduled',
                            'transitions': [
                                {'from': 'scheduled', 'to': 'confirmed', 'label': 'Confirm Appointment'},
                                {'from': 'confirmed', 'to': 'in_progress', 'label': 'Start Appointment'},
                                {'from': 'in_progress', 'to': 'completed', 'label': 'Complete Appointment'},
                                {'from': 'scheduled', 'to': 'cancelled', 'label': 'Cancel Appointment'}
                            ]
                        }
                    }
                },
                'default_rule_templates': {
                    'appointment_reminder': {
                        'name': 'Appointment Reminder Rule',
                        'description': 'Automatically send reminders for upcoming appointments',
                        'trigger_type': 'time_based',
                        'conditions': [
                            {
                                'field': 'appointment_date',
                                'operator': 'is_before',
                                'value': '24_hours_from_now'
                            }
                        ],
                        'actions': [
                            {
                                'type': 'send_notification',
                                'config': {
                                    'message': 'Reminder: You have an appointment tomorrow at {appointment_time}',
                                    'channel': 'sms'
                                }
                            }
                        ]
                    },
                    'follow_up_schedule': {
                        'name': 'Follow-up Scheduling Rule',
                        'description': 'Automatically schedule follow-up appointments',
                        'trigger_type': 'context_change',
                        'conditions': [
                            {
                                'field': 'appointment_status',
                                'operator': 'equals',
                                'value': 'completed'
                            }
                        ],
                        'actions': [
                            {
                                'type': 'schedule_follow_up',
                                'config': {
                                    'delay_days': 30,
                                    'appointment_type': 'follow_up'
                                }
                            }
                        ]
                    }
                },
                'base_prompt_template': 'You are a medical practice assistant for {workspace_name}. You help patients with appointment scheduling, medical inquiries, and general practice information. Always maintain patient confidentiality and direct medical questions to healthcare professionals.',
                'personality_defaults': {
                    'tone': 'professional',
                    'style': 'caring',
                    'empathy_level': 'high',
                    'response_length': 'medium',
                    'medical_knowledge': 'basic'
                },
                'conversation_flow': {
                    'greeting': 'Welcome to {workspace_name}. How can I assist you today?',
                    'appointment_booking': 'I can help you schedule an appointment. What type of visit do you need?',
                    'medical_inquiry': 'For medical questions, I recommend speaking directly with our healthcare team.',
                    'closing': 'Is there anything else I can help you with today?'
                },
                'recommended_integrations': {
                    'calendar': 'Google Calendar, Outlook',
                    'emr': 'Epic, Cerner, Practice Fusion',
                    'communication': 'Twilio, SendGrid',
                    'payment': 'Stripe, Square'
                },
                'compliance_requirements': {
                    'hipaa': 'Must maintain patient confidentiality',
                    'data_retention': 'Medical records must be kept for 7+ years',
                    'consent': 'Explicit consent required for communications'
                },
                'best_practices': [
                    'Always verify patient identity before sharing information',
                    'Use secure communication channels',
                    'Maintain detailed conversation logs',
                    'Escalate complex medical questions to staff'
                ],
                'is_featured': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Created Healthcare template')
        else:
            self.stdout.write('✅ Healthcare template already exists')
        
        # Restaurant Template
        restaurant_template, created = BusinessTypeTemplate.objects.get_or_create(
            name='Restaurant Order & Reservation Bot',
            industry='restaurant',
            defaults={
                'description': 'Complete solution for restaurants including order management, reservations, and customer service',
                'default_schema_templates': {
                    'order_management': {
                        'name': 'Order Management Schema',
                        'description': 'Track customer orders, preferences, and delivery information',
                        'fields': [
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'order_type',
                                'type': 'choice',
                                'label': 'Order Type',
                                'required': True,
                                'choices': ['dine_in', 'takeout', 'delivery']
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'delivery_address',
                                'type': 'textarea',
                                'label': 'Delivery Address',
                                'required': False,
                                'conditional': {
                                    'field': 'order_type',
                                    'value': 'delivery'
                                }
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'special_instructions',
                                'type': 'textarea',
                                'label': 'Special Instructions',
                                'required': False
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'order_status',
                                'type': 'status',
                                'label': 'Order Status',
                                'required': True,
                                'choices': ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
                            }
                        ],
                        'status_workflow': {
                            'default_status': 'pending',
                            'transitions': [
                                {'from': 'pending', 'to': 'confirmed', 'label': 'Confirm Order'},
                                {'from': 'confirmed', 'to': 'preparing', 'label': 'Start Preparing'},
                                {'from': 'preparing', 'to': 'ready', 'label': 'Order Ready'},
                                {'from': 'ready', 'to': 'delivered', 'label': 'Mark Delivered'}
                            ]
                        }
                    }
                },
                'default_rule_templates': {
                    'order_confirmation': {
                        'name': 'Order Confirmation Rule',
                        'description': 'Automatically confirm orders and send confirmation messages',
                        'trigger_type': 'context_change',
                        'conditions': [
                            {
                                'field': 'order_status',
                                'operator': 'equals',
                                'value': 'confirmed'
                            }
                        ],
                        'actions': [
                            {
                                'type': 'send_notification',
                                'config': {
                                    'message': 'Your order has been confirmed! Estimated ready time: {estimated_time}',
                                    'channel': 'sms'
                                }
                            }
                        ]
                    }
                },
                'base_prompt_template': 'You are a restaurant assistant for {workspace_name}. You help customers with orders, reservations, menu questions, and general inquiries. Be friendly and helpful while providing accurate information about our offerings.',
                'personality_defaults': {
                    'tone': 'friendly',
                    'style': 'casual',
                    'empathy_level': 'medium',
                    'response_length': 'short',
                    'food_knowledge': 'high'
                },
                'conversation_flow': {
                    'greeting': 'Welcome to {workspace_name}! What can I help you with today?',
                    'menu_inquiry': 'I can tell you about our menu items and help you place an order.',
                    'reservation': 'I can help you make a reservation. What date and time works for you?',
                    'closing': 'Thank you for choosing {workspace_name}! Enjoy your meal!'
                },
                'recommended_integrations': {
                    'pos': 'Square, Toast, Clover',
                    'delivery': 'DoorDash, Uber Eats, Grubhub',
                    'reservations': 'OpenTable, Resy',
                    'communication': 'Twilio, SendGrid'
                },
                'compliance_requirements': {
                    'food_safety': 'Must follow local health department guidelines',
                    'allergen_info': 'Provide accurate allergen information',
                    'pricing': 'Display accurate pricing and fees'
                },
                'best_practices': [
                    'Always confirm order details before processing',
                    'Provide accurate wait time estimates',
                    'Handle special dietary requests carefully',
                    'Maintain friendly, helpful tone'
                ],
                'is_featured': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Created Restaurant template')
        else:
            self.stdout.write('✅ Restaurant template already exists')
        
        # E-commerce Template
        ecommerce_template, created = BusinessTypeTemplate.objects.get_or_create(
            name='E-commerce Customer Support',
            industry='ecommerce',
            defaults={
                'description': 'Complete solution for online stores including order tracking, customer support, and product inquiries',
                'default_schema_templates': {
                    'order_tracking': {
                        'name': 'Order Tracking Schema',
                        'description': 'Track customer orders, shipping status, and delivery information',
                        'fields': [
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'order_number',
                                'type': 'text',
                                'label': 'Order Number',
                                'required': True
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'shipping_status',
                                'type': 'status',
                                'label': 'Shipping Status',
                                'required': True,
                                'choices': ['processing', 'shipped', 'in_transit', 'delivered', 'returned']
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'tracking_number',
                                'type': 'text',
                                'label': 'Tracking Number',
                                'required': False
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'delivery_date',
                                'type': 'date',
                                'label': 'Expected Delivery Date',
                                'required': False
                            }
                        ],
                        'status_workflow': {
                            'default_status': 'processing',
                            'transitions': [
                                {'from': 'processing', 'to': 'shipped', 'label': 'Mark Shipped'},
                                {'from': 'shipped', 'to': 'in_transit', 'label': 'In Transit'},
                                {'from': 'in_transit', 'to': 'delivered', 'label': 'Mark Delivered'}
                            ]
                        }
                    }
                },
                'default_rule_templates': {
                    'shipping_update': {
                        'name': 'Shipping Update Rule',
                        'description': 'Automatically notify customers of shipping updates',
                        'trigger_type': 'context_change',
                        'conditions': [
                            {
                                'field': 'shipping_status',
                                'operator': 'changes_to',
                                'value': ['shipped', 'delivered']
                            }
                        ],
                        'actions': [
                            {
                                'type': 'send_notification',
                                'config': {
                                    'message': 'Your order status has been updated to: {shipping_status}',
                                    'channel': 'email'
                                }
                            }
                        ]
                    }
                },
                'base_prompt_template': 'You are a customer support specialist for {workspace_name}, an online store. You help customers with orders, product questions, shipping information, and general support. Be helpful and efficient while providing accurate information.',
                'personality_defaults': {
                    'tone': 'helpful',
                    'style': 'professional',
                    'empathy_level': 'high',
                    'response_length': 'medium',
                    'product_knowledge': 'high'
                },
                'conversation_flow': {
                    'greeting': 'Hello! Welcome to {workspace_name} customer support. How can I help you today?',
                    'order_inquiry': 'I can help you track your order or answer questions about your purchase.',
                    'product_help': 'I can provide information about our products and help you find what you need.',
                    'closing': 'Is there anything else I can help you with? Thank you for choosing {workspace_name}!'
                },
                'recommended_integrations': {
                    'ecommerce': 'Shopify, WooCommerce, Magento',
                    'shipping': 'ShipStation, EasyPost, Shippo',
                    'communication': 'Zendesk, Intercom, Freshdesk',
                    'analytics': 'Google Analytics, Mixpanel'
                },
                'compliance_requirements': {
                    'data_privacy': 'GDPR compliance for EU customers',
                    'shipping_info': 'Provide accurate shipping costs and times',
                    'return_policy': 'Clear return and refund policies'
                },
                'best_practices': [
                    'Always verify order details before providing information',
                    'Provide accurate shipping estimates',
                    'Handle returns and refunds professionally',
                    'Maintain detailed conversation logs'
                ],
                'is_featured': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Created E-commerce template')
        else:
            self.stdout.write('✅ E-commerce template already exists')
        
        # Technology/SaaS Template
        tech_template, created = BusinessTypeTemplate.objects.get_or_create(
            name='SaaS Customer Success Bot',
            industry='technology',
            defaults={
                'description': 'Complete solution for software companies including onboarding, support, and feature guidance',
                'default_schema_templates': {
                    'customer_success': {
                        'name': 'Customer Success Schema',
                        'description': 'Track customer onboarding, usage patterns, and support needs',
                        'fields': [
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'onboarding_stage',
                                'type': 'choice',
                                'label': 'Onboarding Stage',
                                'required': True,
                                'choices': ['not_started', 'in_progress', 'completed', 'advanced']
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'feature_usage',
                                'type': 'multi_choice',
                                'label': 'Features Used',
                                'required': False,
                                'choices': ['dashboard', 'analytics', 'integrations', 'api', 'mobile_app']
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'support_tickets',
                                'type': 'number',
                                'label': 'Support Tickets',
                                'required': False
                            },
                            {
                                'id': str(uuid.uuid4()),
                                'name': 'customer_status',
                                'type': 'status',
                                'label': 'Customer Status',
                                'required': True,
                                'choices': ['trial', 'active', 'at_risk', 'churned']
                            }
                        ],
                        'status_workflow': {
                            'default_status': 'trial',
                            'transitions': [
                                {'from': 'trial', 'to': 'active', 'label': 'Convert to Active'},
                                {'from': 'active', 'to': 'at_risk', 'label': 'Flag At Risk'},
                                {'from': 'at_risk', 'to': 'active', 'label': 'Recover Customer'},
                                {'from': 'active', 'to': 'churned', 'label': 'Mark Churned'}
                            ]
                        }
                    }
                },
                'default_rule_templates': {
                    'onboarding_check': {
                        'name': 'Onboarding Check Rule',
                        'description': 'Automatically check onboarding progress and offer help',
                        'trigger_type': 'time_based',
                        'conditions': [
                            {
                                'field': 'onboarding_stage',
                                'operator': 'equals',
                                'value': 'not_started'
                            },
                            {
                                'field': 'days_since_signup',
                                'operator': 'greater_than',
                                'value': 3
                            }
                        ],
                        'actions': [
                            {
                                'type': 'send_notification',
                                'config': {
                                    'message': 'Welcome to {workspace_name}! Let me help you get started.',
                                    'channel': 'in_app'
                                }
                            }
                        ]
                    }
                },
                'base_prompt_template': 'You are a customer success specialist for {workspace_name}, a software company. You help customers with onboarding, feature questions, troubleshooting, and best practices. Be technical but approachable.',
                'personality_defaults': {
                    'tone': 'technical',
                    'style': 'helpful',
                    'empathy_level': 'high',
                    'response_length': 'detailed',
                    'technical_knowledge': 'expert'
                },
                'conversation_flow': {
                    'greeting': 'Hello! I\'m here to help you get the most out of {workspace_name}. What can I assist you with?',
                    'onboarding': 'I can guide you through our onboarding process and help you get started quickly.',
                    'feature_help': 'I can explain our features and show you how to use them effectively.',
                    'closing': 'Is there anything else you\'d like to know about {workspace_name}?'
                },
                'recommended_integrations': {
                    'analytics': 'Mixpanel, Amplitude, Google Analytics',
                    'support': 'Zendesk, Intercom, Freshdesk',
                    'onboarding': 'Appcues, Userflow, Pendo',
                    'communication': 'Slack, Microsoft Teams'
                },
                'compliance_requirements': {
                    'data_security': 'SOC 2 compliance for enterprise customers',
                    'privacy': 'GDPR and CCPA compliance',
                    'accessibility': 'WCAG 2.1 AA compliance'
                },
                'best_practices': [
                    'Always verify customer identity before accessing account info',
                    'Provide step-by-step guidance for complex features',
                    'Escalate technical issues to engineering team',
                    'Track customer engagement and satisfaction'
                ],
                'is_featured': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write('✅ Created Technology/SaaS template')
        else:
            self.stdout.write('✅ Technology/SaaS template already exists')
        
        self.stdout.write('\n🎉 Business template setup complete!')
        self.stdout.write('=' * 50)
        self.stdout.write('Created templates:')
        self.stdout.write('  - Healthcare: Medical Practice Assistant')
        self.stdout.write('  - Restaurant: Order & Reservation Bot')
        self.stdout.write('  - E-commerce: Customer Support')
        self.stdout.write('  - Technology: SaaS Customer Success Bot')
        self.stdout.write('')
        self.stdout.write('These templates include:')
        self.stdout.write('  ✅ Pre-built context schemas')
        self.stdout.write('  ✅ Business rule templates')
        self.stdout.write('  ✅ AI agent configurations')
        self.stdout.write('  ✅ Industry-specific prompts')
        self.stdout.write('  ✅ Compliance requirements')
        self.stdout.write('  ✅ Best practices')
        self.stdout.write('')
        self.stdout.write('You can now apply these templates to workspaces using the dashboard!')
