from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'evidence', views.EvidenceViewSet, basename='evidence')
router.register(r'requests', views.RequestViewSet, basename='request')
router.register(r'factory/requests', views.FactoryRequestViewSet, basename='factory-request')

app_name = 'core'

urlpatterns = [
    path('', include(router.urls)),
]
