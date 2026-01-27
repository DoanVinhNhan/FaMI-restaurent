from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Ingredient(models.Model):
    """
    Represents raw materials used to prepare menu items.
    Corresponds to Table 2.3 in the specification.
    """
    
    # Implicit id (Auto field) maps to 'ingredientId' in specs
    
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("SKU"),
        help_text=_("Stock Keeping Unit for internal management")
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name=_("Ingredient Name")
    )
    
    unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Unit of Measure"),
        help_text=_("e.g., kg, liter, piece")
    )
    
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Cost Per Unit"),
        help_text=_("Cost price per unit of measure")
    )
    
    alert_threshold = models.IntegerField(
        default=0,
        verbose_name=_("Alert Threshold"),
        help_text=_("Minimum stock level to trigger low stock warning")
    )

    class Meta:
        verbose_name = _("Ingredient")
        verbose_name_plural = _("Ingredients")
        db_table = "ingredients"  # Explicit table name from specs
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class InventoryItem(models.Model):
    """
    Manages the actual quantity on hand for a specific ingredient.
    Corresponds to Table 2.10 in the specification.
    
    Design Note: The specification indicates 'itemId' is PK and FK to Ingredients.
    This implies a One-to-One relationship.
    """
    
    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="inventory_stock",
        db_column="itemId",
        verbose_name=_("Ingredient")
    )
    
    quantity_on_hand = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Quantity On Hand")
    )
    
    storage_location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Storage Location"),
        help_text=_("Physical location in the warehouse/kitchen")
    )

    class Meta:
        verbose_name = _("Inventory Item")
        verbose_name_plural = _("Inventory Items")
        db_table = "inventory_items"

    def __str__(self) -> str:
        return f"Stock for {self.ingredient.name}: {self.quantity_on_hand} {self.ingredient.unit}"

    def is_low_stock(self) -> bool:
        """Checks if current stock is below the ingredient's alert threshold."""
        return self.quantity_on_hand <= self.ingredient.alert_threshold

class InventoryLog(models.Model):
    """
    Tracks manual adjustments or auto-changes to inventory.
    """
    id = models.AutoField(primary_key=True)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    change_type = models.CharField(max_length=50, default='ADJUSTMENT')
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ingredient.name} change: {self.quantity_change}"


# --- Stock Taking Models (Task 024) ---
from decimal import Decimal
import uuid
from django.conf import settings

class StockTakeTicket(models.Model):
    """
    Header model for a stock taking session.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    ticket_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    code = models.CharField(
        max_length=50, 
        unique=True,
        help_text=_("Human readable code, e.g., ST-20231027-001")
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_take_tickets',
        help_text=_("User who initiated the stock take")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    variance_total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Stock Take Ticket")
        verbose_name_plural = _("Stock Take Tickets")

    def __str__(self) -> str:
        return f"{self.code} [{self.status}]"

    def calculate_total_variance(self) -> Decimal:
        total = Decimal('0.00')
        if hasattr(self, 'details'):
            for detail in self.details.all():
                cost = detail.ingredient.cost_per_unit
                variance_qty = detail.variance
                total += (variance_qty * cost)
        return total


class StockTakeDetail(models.Model):
    """
    Line items for a stock take ticket.
    """
    ticket = models.ForeignKey(
        StockTakeTicket,
        on_delete=models.CASCADE,
        related_name='details'
    )
    ingredient = models.ForeignKey(
        'inventory.Ingredient', # String reference
        on_delete=models.PROTECT,
        related_name='stock_take_history'
    )
    snapshot_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Theoretical quantity in system at the time of ticket creation")
    )
    actual_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    variance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('ticket', 'ingredient')
        verbose_name = _("Stock Take Detail")
        verbose_name_plural = _("Stock Take Details")

    def __str__(self) -> str:
        return f"{self.ticket.code} - {self.ingredient.name}"

    def save(self, *args, **kwargs) -> None:
        if self.actual_quantity is not None:
            self.variance = self.actual_quantity - self.snapshot_quantity
        super().save(*args, **kwargs)
