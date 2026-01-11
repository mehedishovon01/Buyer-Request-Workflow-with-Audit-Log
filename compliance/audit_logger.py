from users.models import AuditLog
from django.utils import timezone

def log_action(actor, action, object_type, object_id, **metadata):
    """
    Helper function to create audit log entries consistently
    
    Args:
        actor: The user performing the action (User instance)
        action: The action being performed (from AuditLog.Action)
        object_type: The type of object being acted upon (from AuditLog.ObjectType)
        object_id: The ID of the object being acted upon
        **metadata: Additional metadata to include in the log
    """
    # Add actor information to metadata
    metadata.update({
        'actorUserId': actor.user_id,
        'actorRole': actor.role,
        'timestamp': timezone.now().isoformat()
    })
    
    # Create the audit log entry
    AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        metadata=metadata
    )

def log_evidence_creation(actor, evidence):
    """Log the creation of evidence"""
    log_action(
        actor=actor,
        action=AuditLog.Action.CREATE,
        object_type=AuditLog.ObjectType.EVIDENCE,
        object_id=evidence.id,
        factoryId=evidence.factory.user_id,
        docType=evidence.doc_type,
        evidenceId=str(evidence.id)
    )

def log_version_addition(actor, version):
    """Log the addition of a new version to evidence"""
    log_action(
        actor=actor,
        action=AuditLog.Action.CREATE,
        object_type=AuditLog.ObjectType.VERSION,
        object_id=version.id,
        evidenceId=str(version.evidence.id),
        factoryId=version.evidence.factory.user_id,
        versionNumber=version.version_number
    )

def log_request_creation(actor, request_obj):
    """Log the creation of a request"""
    log_action(
        actor=actor,
        action=AuditLog.Action.CREATE,
        object_type=AuditLog.ObjectType.REQUEST,
        object_id=request_obj.id,
        buyerId=request_obj.buyer.user_id,
        factoryId=request_obj.factory.user_id,
        title=request_obj.title
    )

def log_request_status_change(actor, request_obj, old_status, new_status):
    """Log a status change for a request"""
    log_action(
        actor=actor,
        action=AuditLog.Action.UPDATE,
        object_type=AuditLog.ObjectType.REQUEST,
        object_id=request_obj.id,
        buyerId=request_obj.buyer.user_id,
        factoryId=request_obj.factory.user_id,
        statusChange={
            'from': old_status,
            'to': new_status
        }
    )

def log_request_item_fulfillment(actor, request_item):
    """Log the fulfillment of a request item"""
    log_action(
        actor=actor,
        action=AuditLog.Action.UPDATE,
        object_type=AuditLog.ObjectType.REQUEST_ITEM,
        object_id=request_item.id,
        requestId=str(request_item.request.id),
        buyerId=request_item.request.buyer.user_id,
        factoryId=request_item.request.factory.user_id,
        docType=request_item.doc_type,
        evidenceId=str(request_item.evidence_version.evidence.id) if request_item.evidence_version else None,
        versionId=str(request_item.evidence_version.id) if request_item.evidence_version else None,
        statusChange={
            'from': 'pending',
            'to': 'fulfilled'
        }
    )

def log_download(actor, obj, obj_type, **metadata):
    """Log a download action"""
    log_action(
        actor=actor,
        action=AuditLog.Action.DOWNLOAD,
        object_type=obj_type,
        object_id=obj.id,
        **metadata
    )
