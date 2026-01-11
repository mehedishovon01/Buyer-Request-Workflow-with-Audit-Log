"""
URL configuration for config project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from config import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Buyer Request System API",
        default_version='v1',
        description="API for managing buyer requests and evidence documents",
        terms_of_service="http://127.0.0.1:8000/terms/",
        contact=openapi.Contact(email="mehedishovon01@gmail.com"),
        license=openapi.License(name="Enterprise License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Main URL patterns
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
     
    # API endpoints
    path(f'api/{settings.API_VERSION}/auth/', include('users.urls')),  # Authentication endpoints
    path(f'api/{settings.API_VERSION}/compliance/', include('compliance.urls')),  # Core API endpoints

    # API Documentation
    re_path(rf'^api/{settings.API_VERSION}/schema/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path(f'api/{settings.API_VERSION}/schema/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path(f'api/{settings.API_VERSION}/schema/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
