from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class ReasonCode(models.Model):
    """
    Represents standardized reasons for waste or cancellations.
    Table 2.13: ReasonCodes
    """
    code = models.CharField(
        max_length=50, 
        primary_key=True, 
        help_text=_("Unique code for the reason (e.g., BURN, EXPIRED).")
    )
    description = models.TextField(
        help_text=_("Detailed description of the reason.")
    )

    class Meta:
        verbose_name = _("Reason Code")
        verbose_name_plural = _("Reason Codes")

    def __str__(self) -> str:
        return f"{self.code} - {self.description[:30]}"


class WasteReport(models.Model):
    """
    Logs kitchen waste events.
    Table 2.13: WasteReports
    """
    log_id = models.AutoField(primary_key=True)
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='waste_reports',
        help_text=_("The user (Kitchen Staff) reporting the waste.")
    )
    
    # Generic Foreign Key to allow wasting either an Ingredient OR a MenuItem
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text=_("Quantity wasted.")
    )
    
    reason = models.ForeignKey(
        'ReasonCode',
        on_delete=models.PROTECT,
        related_name='waste_reports',
        help_text=_("Standardized reason for the waste.")
    )
    
    reported_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the report was created.")
    )

    loss_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text=_("Calculated financial loss.")
    )

    class Meta:
        verbose_name = _("Waste Report")
        verbose_name_plural = _("Waste Reports")
        ordering = ['-reported_at']

    def __str__(self) -> str:
        return f"Waste: {self.content_object} x{self.quantity} ({self.reason_id})"


class StatusHistory(models.Model):
    """
    Tracks status changes for order details (e.g., Pending -> Cooking -> Done).
    Table 2.14: StatusHistories
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'Pending', _('Pending')
        COOKING = 'Cooking', _('Cooking')
        READY = 'Ready', _('Ready') # Equivalent to DONE
        SERVED = 'Served', _('Served')
        CANCELLED = 'Cancelled', _('Cancelled')

    history_id = models.AutoField(primary_key=True)
    
    # Referencing 'sales' app for OrderDetail.
    order_detail = models.ForeignKey(
        'sales.OrderDetail',
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text=_("The specific line item in an order.")
    )
    
    old_status = models.CharField(
        max_length=50,
        help_text=_("Status before the change.")
    )
    
    new_status = models.CharField(
        max_length=50,
        help_text=_("Status after the change.")
    )
    
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp of the status change.")
    )
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes',
        help_text=_("User who triggered the status change.")
    )

    class Meta:
        verbose_name = _("Status History")
        verbose_name_plural = _("Status Histories")
        ordering = ['-changed_at']

    def __str__(self) -> str:
        return f"{self.order_detail_id}: {self.old_status} -> {self.new_status}"
