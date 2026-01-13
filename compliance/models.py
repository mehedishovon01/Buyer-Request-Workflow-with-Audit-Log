from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from users.models import User, AuditLog
from django.db.models import Q


class Evidence(models.Model):
    """
    Represents an evidence document uploaded by a factory
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=100)
    factory = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='evidences',
        limit_choices_to={'role': User.Role.FACTORY}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.doc_type}) - {self.factory.user_id}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        super().save(*args, **kwargs)
        
        # Log the creation of new evidence
        if is_new:
            from .audit_logger import log_evidence_creation
            log_evidence_creation(self.factory, self)


class EvidenceVersion(models.Model):
    """
    Represents a version of an evidence document
    """
    id = models.AutoField(primary_key=True)
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='evidence_uploads/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='evidence_versions_created'
    )
    
    class Meta:
        ordering = ['evidence', '-version_number']
        unique_together = ('evidence', 'version_number')
        
    def can_be_accessed_by(self, user):
        """Check if a user has access to this evidence version"""
        # Factory users can access their own evidence
        if user.role == User.Role.FACTORY and self.evidence.factory == user:
            return True
            
        # Check if this version was shared with the user
        return self.shared_with.filter(user=user).exists()

    def __str__(self):
        return f"{self.evidence.name} v{self.version_number}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            # Set the version number for new versions
            last_version = EvidenceVersion.objects.filter(
                evidence=self.evidence
            ).order_by('-version_number').first()
            self.version_number = last_version.version_number + 1 if last_version else 1
        
        # Set the created_by user if not set
        if not hasattr(self, 'created_by') or not self.created_by:
            self.created_by = self.evidence.factory
        
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Log the addition of a new version
        if is_new:
            from .audit_logger import log_version_addition
            log_version_addition(self.created_by, self)


class Request(models.Model):
    """
    Represents a request from a buyer to a factory for evidence
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    buyer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='buyer_requests',
        limit_choices_to={'role': User.Role.BUYER}
    )
    factory = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='factory_requests',
        limit_choices_to={'role': User.Role.FACTORY}
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.buyer.user_id} → {self.factory.user_id}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_status = None
        
        if not is_new:
            old_status = Request.objects.get(pk=self.pk).status
        
        super().save(*args, **kwargs)
        
        # Import here to avoid circular imports
        from .audit_logger import log_request_creation, log_request_status_change
        
        # Log the creation of a new request
        if is_new:
            log_request_creation(self.buyer, self)
        # Log status changes
        elif old_status and old_status != self.status:
            # Determine who initiated the status change
            actor = self.buyer if self.status == self.Status.CANCELLED else self.factory
            log_request_status_change(actor, self, old_status, self.status)


class RequestItem(models.Model):
    """
    Represents an item in a request, specifying the type of evidence requested
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        FULFILLED = 'fulfilled', _('Fulfilled')
        REJECTED = 'rejected', _('Rejected')
    
    id = models.AutoField(primary_key=True)
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='items')
    doc_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    evidence_version = models.ForeignKey(
        EvidenceVersion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='fulfilled_items'
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='fulfilled_items',
        limit_choices_to={'role': User.Role.FACTORY}
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['request', 'created_at']
    
    def __str__(self):
        return f"{self.request.title} - {self.doc_type} ({self.status})"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_status = None
        
        if not is_new:
            old_status = RequestItem.objects.get(pk=self.pk).status
        
        # Update timestamps when status changes
        if not is_new and old_status != self.status:
            if self.status == self.Status.FULFILLED and not self.fulfilled_at:
                self.fulfilled_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Log status changes
        if not is_new and old_status != self.status:
            if self.status == self.Status.FULFILLED:
                from .audit_logger import log_request_item_fulfillment
                log_request_item_fulfillment(self.fulfilled_by, self)
                
                # Share the evidence version with the buyer
                from .models import SharedEvidence
                SharedEvidence.objects.get_or_create(
                    version=self.evidence_version,
                    user=self.request.buyer,
                    defaults={'shared_by': self.fulfilled_by}
                )
            else:
                # Log other status changes
                from .audit_logger import log_action
                log_action(
                    actor=self.fulfilled_by or self.request.buyer,
                    action=AuditLog.Action.UPDATE,
                    object_type=AuditLog.ObjectType.REQUEST_ITEM,
                    object_id=self.id,
                    requestId=str(self.request.id),
                    buyerId=self.request.buyer.user_id,
                    factoryId=self.request.factory.user_id,
                    docType=self.doc_type,
                    statusChange={
                        'from': old_status,
                        'to': self.status
                    }
                )


class SharedEvidence(models.Model):
    """Tracks which evidence versions are shared with which users"""
    version = models.ForeignKey(
        EvidenceVersion, 
        on_delete=models.CASCADE,
        related_name='shared_with'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_evidence_versions'
    )
    shared_at = models.DateTimeField(auto_now_add=True)
    shared_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='shared_evidence'
    )
    
    class Meta:
        unique_together = ('version', 'user')
        
    def __str__(self):
        return f"{self.version} shared with {self.user}"
