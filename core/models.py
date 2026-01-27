import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# --- User Model ---
class UserRole(models.TextChoices):
    MANAGER = 'MANAGER', _('Restaurant Manager')
    CASHIER = 'CASHIER', _('Cashier')
    KITCHEN = 'KITCHEN', _('Kitchen Crew')
    INVENTORY = 'INVENTORY', _('Inventory Manager')
    ADMIN = 'ADMIN', _('System Admin')

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=50,
        choices=UserRole.choices,
        default=UserRole.CASHIER,
        verbose_name=_("System Role"),
        help_text=_("Designates the role of the user in the restaurant workflow.")
    )
    employee_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Employee Code"),
        help_text=_("Unique identifier for the employee (e.g., EMP001).")
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ['username']

    def __str__(self) -> str:
        if self.employee_code:
            return f"{self.username} ({self.employee_code}) - {self.get_role_display()}"
        return f"{self.username} - {self.get_role_display()}"

    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER or self.is_superuser

    def is_kitchen_crew(self) -> bool:
        return self.role == UserRole.KITCHEN

    def is_inventory_manager(self) -> bool:
        return self.role == UserRole.INVENTORY


# --- System Settings Models ---
class SettingGroup(models.Model):
    group_name = models.CharField(max_length=255, unique=True, help_text=_("Name of the settings group"))
    description = models.TextField(blank=True, null=True, help_text=_("Optional description of what this group controls"))

    class Meta:
        verbose_name = _("Setting Group")
        verbose_name_plural = _("Setting Groups")

    def __str__(self) -> str:
        return self.group_name


class SystemSetting(models.Model):
    class DataType(models.TextChoices):
        STRING = 'STRING', _('String')
        INTEGER = 'INTEGER', _('Integer')
        FLOAT = 'FLOAT', _('Float')
        BOOLEAN = 'BOOLEAN', _('Boolean')
        JSON = 'JSON', _('JSON')

    setting_key = models.CharField(
        max_length=255, 
        primary_key=True, 
        help_text=_("Unique key for the setting (e.g., 'TAX_RATE')")
    )
    setting_value = models.TextField(help_text=_("Value stored as text"))
    data_type = models.CharField(
        max_length=50, 
        choices=DataType.choices, 
        default=DataType.STRING,
        help_text=_("Data type for type casting")
    )
    group = models.ForeignKey(
        SettingGroup, 
        on_delete=models.CASCADE, 
        related_name='settings',
        help_text=_("Group this setting belongs to")
    )
    is_active = models.BooleanField(default=True, help_text=_("Is this setting currently applied?"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("System Setting")
        verbose_name_plural = _("System Settings")

    def __str__(self) -> str:
        return f"{self.setting_key}: {self.setting_value}"


# --- Audit Log Model ---
class AuditLog(models.Model):
    """
    Immutable log entry for system actions.
    Stores actor, action type, target reference, and detailed changes.
    """
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        SYSTEM = 'SYSTEM', _('System Process')
        APPROVE = 'APPROVE', _('Approve')
        REJECT = 'REJECT', _('Reject')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Actor: The user who performed the action (nullable for system background tasks)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_("User who performed the action")
    )

    # Action: What happened
    action = models.CharField(
        max_length=20, 
        choices=ActionType.choices,
        help_text=_("Type of action performed")
    )

    # Target: Generic reference to the object being acted upon
    target_model = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text=_("Name of the model affected (e.g., 'Order', 'MenuItem')")
    )
    target_object_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text=_("Primary key of the affected object")
    )

    # Details: JSON storage for flexibility (Snapshot of data)
    changes = models.JSONField(
        default=dict, 
        blank=True,
        help_text=_("JSON delta or snapshot of the changes")
    )

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")

    def __str__(self) -> str:
        actor_name = self.actor.username if self.actor else "SYSTEM"
        return f"[{self.timestamp}] {actor_name} - {self.action} - {self.target_model}"
