from django.contrib import admin
from .models import (
    Evidence, EvidenceVersion, Request, RequestItem
)

# Register models with BaseAdmin
admin.site.register(Evidence)
admin.site.register(EvidenceVersion)
admin.site.register(Request)
admin.site.register(RequestItem)
