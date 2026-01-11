from rest_framework import serializers
from django.utils import timezone
from users.models import User
from .models import (
    Evidence, EvidenceVersion, Request, RequestItem
)


class EvidenceVersionSerializer(serializers.ModelSerializer):
    """Serializer for EvidenceVersion model"""
    version_number = serializers.IntegerField(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EvidenceVersion
        fields = [
            'id', 'version_number', 'notes', 'expiry_date', 
            'file', 'file_url', 'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_file_url(self, obj):
        if obj.file:
            return self.context['request'].build_absolute_uri(obj.file.url)
        return None


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Evidence model"""
    versions = EvidenceVersionSerializer(many=True, read_only=True)
    factory_name = serializers.CharField(source='factory.user_id', read_only=True)
    
    class Meta:
        model = Evidence
        fields = [
            'id', 'name', 'doc_type', 'factory', 'factory_name',
            'created_at', 'updated_at', 'versions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'factory']


class CreateEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for creating Evidence with initial version"""
    file = serializers.FileField(write_only=True)
    notes = serializers.CharField(write_only=True)
    expiry = serializers.DateField(write_only=True)
    
    class Meta:
        model = Evidence
        fields = ['name', 'doc_type', 'file', 'notes', 'expiry']
    
    def create(self, validated_data):
        # Extract the file, notes, and expiry from the validated data
        file = validated_data.pop('file')
        notes = validated_data.pop('notes')
        expiry = validated_data.pop('expiry')
        
        # Get the factory user from the request
        factory = self.context['request'].user
        
        # Remove factory from validated_data if it exists (shouldn't be needed as it's not in fields)
        validated_data.pop('factory', None)
        
        # Create the evidence
        evidence = Evidence.objects.create(
            **validated_data,
            factory=factory
        )
        
        # Create the initial version
        EvidenceVersion.objects.create(
            evidence=evidence,
            notes=notes,
            expiry_date=expiry,
            file=file,
            created_by=factory
        )
        
        return evidence


class AddVersionSerializer(serializers.ModelSerializer):
    """Serializer for adding a new version to an evidence"""
    class Meta:
        model = EvidenceVersion
        fields = ['notes', 'expiry_date', 'file']
    
    def create(self, validated_data):
        evidence_id = self.context['evidence_id']
        user = self.context['request'].user
        
        # Get the evidence and ensure the user has permission
        evidence = Evidence.objects.get(id=evidence_id)
        if evidence.factory != user:
            raise serializers.ValidationError("You don't have permission to add versions to this evidence.")
        
        # Create the new version
        version = EvidenceVersion.objects.create(
            evidence=evidence,
            created_by=user,
            **validated_data
        )
        
        return version


class RequestItemSerializer(serializers.ModelSerializer):
    """Serializer for RequestItem model"""
    evidence_version = EvidenceVersionSerializer(read_only=True)
    
    class Meta:
        model = RequestItem
        fields = [
            'id', 'doc_type', 'status', 'evidence_version',
            'fulfilled_at', 'fulfilled_by', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'evidence_version', 'fulfilled_at', 'fulfilled_by', 'created_at']


class RequestSerializer(serializers.ModelSerializer):
    """Serializer for Request model"""
    buyer_name = serializers.CharField(source='buyer.user_id', read_only=True)
    factory_name = serializers.CharField(source='factory.user_id', read_only=True)
    items = RequestItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Request
        fields = [
            'id', 'title', 'buyer', 'buyer_name', 'factory', 'factory_name',
            'status', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'buyer']


class CreateRequestSerializer(serializers.Serializer):
    """Serializer for creating a new request"""
    factory_id = serializers.CharField()
    title = serializers.CharField(max_length=255)
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField(),
            allow_empty=False
        ),
        min_length=1
    )
    
    def validate_factory_id(self, value):
        try:
            factory = User.objects.get(
                user_id=value,
                role=User.Role.BUYER
            )
            return factory
        except User.DoesNotExist:
            raise serializers.ValidationError("Factory not found with the given ID.")
    
    def validate_items(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Items must be a list.")
        
        validated_items = []
        for item in value:
            if not isinstance(item, dict) or 'docType' not in item:
                raise serializers.ValidationError("Each item must be a dictionary with a 'docType' key.")
            validated_items.append({
                'doc_type': item['docType']
            })
        
        return validated_items
    
    def create(self, validated_data):
        user = self.context['request'].user
        factory = validated_data['factory_id']  # This is actually the factory object now
        title = validated_data['title']
        items_data = validated_data['items']
        
        # Create the request
        request_obj = Request.objects.create(
            title=title,
            buyer=user,
            factory=factory
        )
        
        # Create request items
        for item_data in items_data:
            RequestItem.objects.create(
                request=request_obj,
                **item_data
            )
        
        return request_obj


class FulfillItemSerializer(serializers.Serializer):
    """Serializer for fulfilling a request item"""
    evidence_id = serializers.IntegerField()
    version_id = serializers.IntegerField()
    
    def validate(self, data):
        evidence_id = data['evidence_id']
        version_id = data['version_id']
        
        try:
            # Verify the evidence exists and belongs to the factory
            evidence = Evidence.objects.get(
                id=evidence_id,
                factory=self.context['request'].user
            )
            
            # Verify the version exists and belongs to the evidence
            version = EvidenceVersion.objects.get(
                id=version_id,
                evidence=evidence
            )
            
            data['evidence'] = evidence
            data['version'] = version
            return data
            
        except Evidence.DoesNotExist:
            raise serializers.ValidationError({
                'evidence_id': 'Evidence not found or you do not have permission to use it.'
            })
        except EvidenceVersion.DoesNotExist:
            raise serializers.ValidationError({
                'version_id': 'Version not found for the specified evidence.'
            })
