from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, user_id, role, factory_id=None, password=None, **extra_fields):
        if not user_id:
            raise ValueError(_('The User ID must be set'))
        if role not in [User.Role.BUYER, User.Role.FACTORY, User.Role.ADMIN]:
            raise ValueError(_('Invalid role'))
        if role == User.Role.FACTORY and not factory_id:
            raise ValueError(_('Factory ID is required for factory users'))
        
        user = self.model(
            user_id=user_id,
            role=role,
            factory_id=factory_id if role == User.Role.FACTORY else None,
            **extra_fields
        )
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(user_id, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        BUYER = 'buyer', _('Buyer')
        FACTORY = 'factory', _('Factory')
        ADMIN = 'admin', _('Admin')

    user_id = models.CharField(max_length=50, unique=True, primary_key=True)
    factory_id = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['role']
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.user_id} ({self.get_role_display()})"
    
    def is_buyer(self):
        return self.role == self.Role.BUYER
    
    def is_factory(self):
        return self.role == self.Role.FACTORY
    
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        CREATE = 'create', _('Create')
        UPDATE = 'update', _('Update')
        DELETE = 'delete', _('Delete')
        DOWNLOAD = 'download', _('Download')
        UPLOAD = 'upload', _('Upload')
    
    class ObjectType(models.TextChoices):
        USER = 'user', _('User')
        EVIDENCE = 'evidence', _('Evidence')
        REQUEST = 'request', _('Request')
        REQUEST_ITEM = 'request_item', _('Request Item')
        VERSION = 'version', _('Version')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=Action.choices)
    object_type = models.CharField(max_length=20, choices=ObjectType.choices)
    object_id = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.actor} {self.get_action_display()} {self.object_type} {self.object_id}"
