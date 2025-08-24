from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Workspace
from context_tracking.models import ContextCase, CaseTypeConfiguration, CaseMatchingRule
from context_tracking.case_service import CaseManagementService

class Command(BaseCommand):
    help = "Test the Dynamic Case Management System"
    
    def handle(self, *args, **options):
        self.stdout.write("Testing Dynamic Case Management System...")
        
        # Create test workspace if it doesn't exist
        workspace, created = Workspace.objects.get_or_create(
            name="Test Workspace for Case Management",
            defaults={
                "industry": "Technology",
                "owner_name": "Test Owner"
            }
        )
        
        if created:
            self.stdout.write(f"Created test workspace: {workspace.name}")
        else:
            self.stdout.write(f"Using existing workspace: {workspace.name}")
        
        # Create test case type configuration
        case_type_config, created = CaseTypeConfiguration.objects.get_or_create(
            workspace=workspace,
            case_type="sales_lead",
            defaults={
                "display_name": "Sales Lead",
                "description": "Sales lead tracking and management",
                "data_schema": {
                    "customer_name": {"type": "string", "required": True},
                    "email": {"type": "email", "required": True},
                    "phone": {"type": "phone", "required": False},
                    "company": {"type": "string", "required": False},
                    "product_interest": {"type": "string", "required": True}
                },
                "required_fields": ["customer_name", "email", "product_interest"],
                "optional_fields": ["phone", "company"],
                "display_fields": ["customer_name", "email", "company", "product_interest"],
                "status_workflow": ["open", "in_progress", "closed"],
                "default_status": "open",
                "default_priority": "medium"
            }
        )
        
        if created:
            self.stdout.write(f"Created case type configuration: {case_type_config.case_type}")
        else:
            self.stdout.write(f"Using existing case type configuration: {case_type_config.case_type}")
        
        # Create test case matching rule
        matching_rule, created = CaseMatchingRule.objects.get_or_create(
            workspace=workspace,
            rule_name="Email-based Lead Matching",
            case_type="sales_lead",
            defaults={
                "matching_fields": ["email", "customer_name"],
                "matching_strategy": "hybrid",
                "similarity_threshold": 0.8,
                "field_weights": {"email": 0.9, "customer_name": 0.7},
                "action_on_match": "update"
            }
        )
        
        if created:
            self.stdout.write(f"Created matching rule: {matching_rule.rule_name}")
        else:
            self.stdout.write(f"Using existing matching rule: {matching_rule.rule_name}")
        
        # Test case creation
        test_case = ContextCase.objects.create(
            workspace=workspace,
            case_type="sales_lead",
            status="open",
            priority="medium",
            extracted_data={
                "customer_name": "John Doe",
                "email": "john.doe@example.com",
                "company": "Test Corp",
                "product_interest": "AI Solutions"
            },
            confidence_score=0.9,
            source_channel="website"
        )
        
        self.stdout.write(f"Created test case: {test_case.case_id}")
        
        # Test case service
        case_service = CaseManagementService(workspace)
        
        # Test case summary
        cases_summary = case_service.get_cases_summary()
        self.stdout.write(f"Found {len(cases_summary)} cases in workspace")
        
        # Test case details
        case_details = case_service.get_case_details(test_case.case_id)
        if case_details:
            self.stdout.write(f"Case details retrieved successfully: {case_details['case_id']}")
        else:
            self.stdout.write("Failed to retrieve case details")
        
        # Test case statistics
        stats = case_service.get_case_statistics()
        self.stdout.write(f"Case statistics: {stats}")
        
        self.stdout.write(self.style.SUCCESS("Dynamic Case Management System test completed successfully!"))
        
        # Cleanup test data
        test_case.delete()
        self.stdout.write("Test case cleaned up")
