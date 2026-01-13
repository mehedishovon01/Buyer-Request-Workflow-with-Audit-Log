from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.models import User, AuditLog
from .models import Evidence, EvidenceVersion, Request, RequestItem
from .serializers import (
    EvidenceSerializer, CreateEvidenceSerializer, AddVersionSerializer,
    RequestSerializer, CreateRequestSerializer, FulfillItemSerializer,
    RequestItemSerializer
)


class EvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing evidence documents.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Evidence.objects.none()
            
        user = self.request.user
        
        # Factories can only see their own evidence
        if user.role == User.Role.FACTORY:
            return Evidence.objects.filter(factory=user)
            
        # Buyers can only see evidence that has been shared with them
        if user.role == User.Role.BUYER:
            # Get IDs of all evidence versions shared with this user
            shared_evidence_ids = EvidenceVersion.objects.filter(
                shared_with__user=user
            ).values_list('evidence_id', flat=True)
            
            return Evidence.objects.filter(id__in=shared_evidence_ids)
            
        # Admins can see all evidence
        return Evidence.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateEvidenceSerializer
        return EvidenceSerializer
    
    def perform_create(self, serializer):
        # Only factory users can create evidence
        if self.request.user.role != User.Role.FACTORY:
            raise serializers.ValidationError({
                "detail": "Only factory users can create evidence."
            }, code='permission_denied')
        serializer.save(factory=self.request.user)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        List all versions of an evidence document that the user has access to
        """
        evidence = self.get_object()
        user = request.user
        
        # Check if user has access to this evidence
        if user.role == User.Role.BUYER and not evidence.versions.filter(
            shared_with__user=user
        ).exists() and evidence.factory != user:
            return Response(
                {"detail": "You don't have permission to view this evidence."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all versions, filtered by access if buyer
        versions = evidence.versions.all()
        if user.role == User.Role.BUYER:
            versions = versions.filter(shared_with__user=user)
        
        serializer = EvidenceVersionSerializer(
            versions, 
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_version(self, request, pk=None):
        """
        Add a new version to an existing evidence document.
        POST /evidence/:id/versions/
        """
        evidence = self.get_object()
        
        # Check permissions
        if request.user.role != User.Role.FACTORY:
            return Response(
                {"detail": "Only factory users can add versions to evidence."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if evidence.factory != request.user:
            return Response(
                {"detail": "You can only add versions to your own evidence."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AddVersionSerializer(
            data=request.data,
            context={'request': request, 'evidence_id': evidence.id}
        )
        
        if serializer.is_valid():
            version = serializer.save()
            # Return the evidence with all versions
            evidence_serializer = self.get_serializer(evidence)
            return Response(evidence_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing requests.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Request.objects.none()
            
        user = self.request.user
        
        # Factories can only see requests made to them
        if user.role == User.Role.FACTORY:
            return Request.objects.filter(factory=user)
        # Buyers can see their own requests
        elif user.role == User.Role.BUYER:
            return Request.objects.filter(buyer=user)
        # Admins can see all requests
        return Request.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateRequestSerializer
        return RequestSerializer
    
    def create(self, request, *args, **kwargs):
        # Only buyers can create requests
        if request.user.role != User.Role.BUYER:
            return Response(
                {"detail": "Only buyers can create requests."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Create the request
            request_obj = Request.objects.create(
                title=serializer.validated_data['title'],
                buyer=request.user,
                factory=serializer.validated_data['factory_id']
            )
            
            # Create request items
            for item_data in serializer.validated_data['items']:
                RequestItem.objects.create(
                    request=request_obj,
                    doc_type=item_data['doc_type']
                )
            
            # Return the created request with items
            response_serializer = RequestSerializer(request_obj, context={'request': request})
            headers = self.get_success_headers(response_serializer.data)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """
        Get all items for a specific request.
        GET /requests/:id/items/
        """
        request_obj = self.get_object()
        items = request_obj.items.all()
        serializer = RequestItemSerializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='items/(?P<item_id>[^/.]+)/fulfill')
    def fulfill_item(self, request, pk=None, item_id=None):
        """
        Fulfill a specific request item with an evidence version.
        POST /requests/:id/items/:item_id/fulfill/
        """
        # Get the request and item
        request_obj = self.get_object()
        try:
            item = RequestItem.objects.get(id=item_id, request=request_obj)
        except RequestItem.DoesNotExist:
            return Response(
                {"detail": "Request item not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the user has permission (must be the factory that received the request)
        if request.user != request_obj.factory:
            return Response(
                {"detail": "You do not have permission to fulfill this request item."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate the fulfillment data
        serializer = FulfillItemSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the request item
        version = serializer.validated_data['version']
        item.evidence_version = version
        item.status = RequestItem.Status.FULFILLED
        item.fulfilled_by = request.user
        item.save()
        
        # Check if all items are fulfilled
        all_fulfilled = not request_obj.items.filter(
            status__in=[RequestItem.Status.PENDING, RequestItem.Status.REJECTED]
        ).exists()
        
        if all_fulfilled:
            request_obj.status = Request.Status.COMPLETED
            request_obj.save()
        
        # Return the updated request
        request_serializer = self.get_serializer(request_obj)
        return Response(request_serializer.data, status=status.HTTP_200_OK)


class FactoryRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for factory-specific request endpoints.
    """
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Request.objects.none()
            
        # Only return requests for the current factory user
        if self.request.user.role != User.Role.FACTORY:
            return Request.objects.none()
        return Request.objects.filter(factory=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get all pending requests for the factory.
        GET /factory/requests/pending/
        """
        queryset = self.get_queryset().filter(status=Request.Status.PENDING)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
