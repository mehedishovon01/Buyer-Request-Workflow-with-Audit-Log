from django.contrib import admin
from .models import (
    User, AuditLog
)

# Register models with BaseAdmin
admin.site.register(User)
admin.site.register(AuditLog)
