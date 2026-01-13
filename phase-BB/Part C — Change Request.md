# Part C: Change Request Implementation

## Change Request
**Requirement:** "Buyer can only access evidence versions that were explicitly shared via fulfill or included in a pack."

## Implementation Details

### 1. New Model: SharedEvidence
Added a new model to track sharing relationships between evidence versions and users:

```python
class SharedEvidence(models.Model):
    """Tracks which evidence versions are shared with which users"""
    version = models.ForeignKey(
        EvidenceVersion, 
        on_delete=models.CASCADE,
        related_name='shared_with'  # Access via version.shared_with.all()
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_evidence_versions'  # Access via user.shared_evidence_versions.all()
    )
    shared_at = models.DateTimeField(auto_now_add=True)  # When the sharing occurred
    shared_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='shared_evidence'  # Track who did the sharing
    )
    
    class Meta:
        unique_together = ('version', 'user')  # Prevent duplicate shares
```

### 2. Updated EvidenceVersion Model
Added access control method:

```python
def can_be_accessed_by(self, user):
    """Check if a user has access to this evidence version"""
    # Factory users can access their own evidence
    if user.role == User.Role.FACTORY and self.evidence.factory == user:
        return True
        
    # Check if this version was shared with the user
    return self.shared_with.filter(user=user).exists()
```

### 3. Modified RequestItem Save Logic
When a request item is fulfilled, it now creates a sharing record:

```python
# In RequestItem.save()
if self.status == self.Status.FULFILLED:
    # ... existing fulfillment logic ...
    
    # Share the evidence version with the buyer
    SharedEvidence.objects.get_or_create(
        version=self.evidence_version,
        user=self.request.buyer,
        defaults={'shared_by': self.fulfilled_by}
    )
```

### 4. Updated EvidenceViewSet Access Control

#### QuerySet Filtering
```python
def get_queryset(self):
    user = self.request.user
    
    # Factories see their own evidence
    if user.role == User.Role.FACTORY:
        return Evidence.objects.filter(factory=user)
        
    # Buyers only see shared evidence
    if user.role == User.Role.BUYER:
        shared_evidence_ids = EvidenceVersion.objects.filter(
            shared_with__user=user
        ).values_list('evidence_id', flat=True)
        return Evidence.objects.filter(id__in=shared_evidence_ids)
        
    return Evidence.objects.all()
```

#### Version Access Control
```python
@action(detail=True, methods=['get'])
def versions(self, request, pk=None):
    evidence = self.get_object()
    user = request.user
    
    # Check buyer access
    if user.role == User.Role.BUYER and not evidence.versions.filter(
        shared_with__user=user
    ).exists() and evidence.factory != user:
        return Response(
            {"detail": "You don't have permission to view this evidence."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filter versions based on access
    versions = evidence.versions.all()
    if user.role == User.Role.BUYER:
        versions = versions.filter(shared_with__user=user)
    
    serializer = EvidenceVersionSerializer(versions, many=True, context={'request': request})
    return Response(serializer.data)
```

## Security Considerations

1. **Principle of Least Privilege**: Buyers only see what's explicitly shared
2. **Audit Trail**: All sharing is tracked with timestamps and actors
3. **Defense in Depth**: Multiple layers of access control
4. **Data Integrity**: Unique constraints prevent duplicate shares

## Testing Scenarios

1. **Factory User**
   - Can see all their own evidence
   - Can create new evidence and versions
   - Can fulfill requests, which shares evidence with buyers

2. **Buyer User**
   - Can only see shared evidence versions
   - Cannot access unshared evidence
   - Can see all shared versions of accessible evidence

3. **Admin User**
   - Can see all evidence (maintains oversight)
   - Can manage all sharing relationships
