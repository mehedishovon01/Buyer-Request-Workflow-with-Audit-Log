from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from core.pagination import StandardResultsSetPagination
from .models import AuditLog
from .serializers import UserSerializer, LoginSerializer, AuditLogSerializer
from compliance.audit_logger import log_action


class LoginView(APIView):
    """
    POST /auth/login
    Input: { "userId":"U1", "role":"buyer" | "factory", "factoryId":"F001"(if factory) }
    Output: { "access": "token", "refresh": "token" }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the user and tokens from the serializer
        result = serializer.validated_data
        user = result['user']
        
        # Log the login action
        log_action(
            actor=user,
            action=AuditLog.Action.LOGIN,
            object_type=AuditLog.ObjectType.USER,
            object_id=user.user_id,
            ipAddress=self.request.META.get('REMOTE_ADDR'),
            userAgent=self.request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({
            'access': result['access'],
            'refresh': result['refresh'],
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class AuditLogView(APIView):
    """
    GET /audit
    Returns paginated audit log entries
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of results per page (default: 20, max: 100)
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        # Get pagination class instance
        paginator = self.pagination_class()
        
        # Get filtered and ordered queryset
        queryset = AuditLog.objects.all().order_by('-timestamp')
        
        # Paginate the queryset
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            # If page is specified, return paginated response
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        # Fallback if pagination is not used
        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data)
