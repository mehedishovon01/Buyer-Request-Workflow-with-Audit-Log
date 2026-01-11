from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from .models import User, AuditLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_id', 'role', 'factory_id', 'is_active', 'date_joined')
        read_only_fields = ('is_active', 'date_joined')


class LoginSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=True)
    factory_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        user_id = attrs.get('user_id')
        role = attrs.get('role')
        factory_id = attrs.get('factory_id')

        # For factory users, factory_id is required
        if role == User.Role.FACTORY and not factory_id:
            raise serializers.ValidationError("Factory ID is required for factory users")

        # Get or create user
        user, created = User.objects.get_or_create(
            user_id=user_id,
            defaults={
                'role': role,
                'factory_id': factory_id if role == User.Role.FACTORY else None
            }
        )

        # Update user if role or factory_id changed
        if not created:
            if user.role != role or user.factory_id != factory_id:
                user.role = role
                user.factory_id = factory_id if role == User.Role.FACTORY else None
                user.save(update_fields=['role', 'factory_id'])

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        # Make JWT token
        
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


class AuditLogSerializer(serializers.ModelSerializer):
    actorUserId = serializers.CharField(source='actor.user_id', read_only=True)
    actorRole = serializers.CharField(source='actor.role', read_only=True)
    action = serializers.SerializerMethodField()
    objectType = serializers.CharField(source='object_type')
    objectId = serializers.CharField(source='object_id')
    metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'timestamp',
            'actorUserId',
            'actorRole',
            'action',
            'objectType',
            'objectId',
            'metadata'
        ]
        read_only_fields = fields
    
    def get_action(self, obj):
        # Map action to the required format
        action_map = {
            'create': 'CREATE',
            'update': 'UPDATE',
            'delete': 'DELETE',
            'download': 'DOWNLOAD',
            'fulfill': 'FULFILL_ITEM',
            'login': 'LOGIN',
            'upload': 'UPLOAD'
        }
        
        # Get the base action
        base_action = action_map.get(obj.action.lower(), obj.action.upper())
        
        # Special handling for object-specific actions
        if obj.object_type.lower() == 'request':
            if obj.action.lower() == 'create':
                return 'CREATE_REQUEST'
        elif obj.object_type.lower() == 'evidence':
            if obj.action.lower() == 'create':
                return 'CREATE_EVIDENCE'
        elif obj.object_type.lower() == 'version':
            if obj.action.lower() == 'create':
                return 'ADD_VERSION'
                
        return base_action
    
    def get_metadata(self, obj):
        # Start with a clean metadata dictionary
        clean_metadata = {}
        
        # Get original metadata or empty dict if None
        original_metadata = obj.metadata or {}
        
        # Add factoryId - prioritize actor's factory_id if available
        if obj.actor and obj.actor.factory_id:
            clean_metadata['factoryId'] = obj.actor.factory_id
        elif 'factoryId' in original_metadata:
            clean_metadata['factoryId'] = original_metadata['factoryId']
            
        # Add buyerId for buyers - only if not already in metadata
        if obj.actor and obj.actor.role == 'buyer' and 'buyerId' not in original_metadata:
            clean_metadata['buyerId'] = obj.actor.user_id
        elif 'buyerId' in original_metadata:
            clean_metadata['buyerId'] = original_metadata['buyerId']
            
        # Handle docType for evidence and version objects
        if obj.object_type.lower() in ['evidence', 'version']:
            if 'docType' in original_metadata:
                clean_metadata['docType'] = original_metadata['docType']
            elif hasattr(obj, 'document_type'):
                clean_metadata['docType'] = obj.document_type
            else:
                clean_metadata['docType'] = 'unknown'
        
        # Handle status changes for update actions
        if obj.action.lower() == 'update' and 'changes' in original_metadata:
            changes = original_metadata['changes']
            if isinstance(changes, dict) and 'status' in changes:
                status_changes = changes['status']
                if isinstance(status_changes, (list, tuple)) and len(status_changes) >= 2:
                    clean_metadata['previousStatus'] = status_changes[0]
                    clean_metadata['newStatus'] = status_changes[1]
                elif status_changes is not None:
                    clean_metadata['newStatus'] = status_changes
        
        # Add any additional metadata that wasn't already processed
        # but only if it's not a system field we're already handling
        system_fields = {'factoryId', 'buyerId', 'docType', 'previousStatus', 'newStatus', 'changes'}
        for key, value in original_metadata.items():
            if key not in system_fields and key not in clean_metadata:
                clean_metadata[key] = value
                
        return clean_metadata
