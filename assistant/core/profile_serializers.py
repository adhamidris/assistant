"""
Serializers for user profile setup
"""
from rest_framework import serializers
from .models import Workspace

class ProfileSetupSerializer(serializers.ModelSerializer):
    """Serializer for workspace profile setup"""
    
    class Meta:
        model = Workspace
        fields = [
            'owner_name',
            'owner_occupation', 
            'industry',
            'ai_role',
            'ai_personality',
            'custom_instructions',
            'assistant_name',
            'name'  # Business name
        ]
        
    def validate(self, data):
        """Validate profile data"""
        if not data.get('owner_name'):
            raise serializers.ValidationError("Owner name is required")
        if not data.get('industry'):
            raise serializers.ValidationError("Industry is required")
        return data
        
    def update(self, instance, validated_data):
        """Update workspace profile and mark as completed"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Mark profile as completed
        instance.profile_completed = True
        instance.save()
        
        return instance

class ProfileStatusSerializer(serializers.ModelSerializer):
    """Serializer for checking profile completion status"""
    
    class Meta:
        model = Workspace
        fields = [
            'profile_completed',
            'owner_name',
            'ai_role',
            'ai_personality',
            'assistant_name',
            'name'
        ]
        read_only_fields = fields
