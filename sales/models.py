from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal
import uuid

class RestaurantTable(models.Model):
    """
    Represents a physical table in the restaurant.
    Part of the Sales module.
    """

    class TableStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        OCCUPIED = 'OCCUPIED', _('Occupied')
        RESERVED = 'RESERVED', _('Reserved')
        DIRTY = 'DIRTY', _('Dirty')

    table_id = models.AutoField(
        primary_key=True,
        verbose_name=_("Table ID")
    )
    
    table_name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Table Name"),
        help_text=_("E.g., T-01, VIP-02")
    )
    
    capacity = models.PositiveIntegerField(
        default=4,
        verbose_name=_("Seating Capacity"),
        help_text=_("Maximum number of guests")
    )
    
    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.AVAILABLE,
        verbose_name=_("Current Status")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated")
    )

    class Meta:
        verbose_name = _("Restaurant Table")
        verbose_name_plural = _("Restaurant Tables")
        ordering = ['table_name']

    def __str__(self) -> str:
        return f"{self.table_name} ({self.get_status_display()})"

    def is_available(self) -> bool:
        """Check if table is available for seating."""
        return self.status == self.TableStatus.AVAILABLE


# --- Promotion Models ---

class DiscountType(models.TextChoices):
    PERCENTAGE = 'PERCENTAGE', _('Percentage')
    FIXED_AMOUNT = 'FIXED_AMOUNT', _('Fixed Amount')

class Promotion(models.Model):
    """
    Represents a marketing promotion or coupon code.
    UC2: Manage Promotions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Many-to-Many relationship with MenuItem
    eligible_items = models.ManyToManyField(
        'menu.MenuItem',
        through='PromotionDetail',
        related_name='promotions',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Promotion")
        verbose_name_plural = _("Promotions")
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.name} ({self.promo_code})"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("End date must be after start date."))
        if self.discount_type == DiscountType.PERCENTAGE:
            if self.discount_value < 0 or self.discount_value > 100:
                raise ValidationError(_("Percentage discount must be between 0 and 100."))
        else:
            if self.discount_value < 0:
                raise ValidationError(_("Fixed discount cannot be negative."))

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def is_valid(self) -> bool:
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class PromotionDetail(models.Model):
    """
    Intermediate table mapping Promotions to MenuItems.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        Promotion, 
        on_delete=models.CASCADE,
        related_name='promotion_details'
    )
    menu_item = models.ForeignKey(
        'menu.MenuItem', 
        on_delete=models.CASCADE,
        related_name='promotion_details'
    )

    class Meta:
        verbose_name = _("Promotion Detail")
        verbose_name_plural = _("Promotion Details")
        unique_together = ('promotion', 'menu_item')

    def __str__(self) -> str:
        return f"{self.promotion.promo_code} - {self.menu_item}"


# --- Order Models ---

class Order(models.Model):
    """
    Represents the header of a sales order.
    Corresponds to Table 2.4 in the System Design Document.
    """

    class Status(models.TextChoices):
        PENDING = 'Pending', _('Pending')       # Order created
        COOKING = 'Cooking', _('Cooking')       # Sent to kitchen
        PAID = 'Paid', _('Paid')                # Payment completed
        CANCELLED = 'Cancelled', _('Cancelled') # Order voided

    # External ID for Idempotency
    external_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text=_("External System ID for idempotent creation.")
    )

    # Relations
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text=_("The table associated with this order.")
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='processed_orders',
        help_text=_("The staff member (Cashier/Manager) who created the order.")
    )

    # Financials
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total calculated amount for the order.")
    )

    # State
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Current processing status of the order.")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self) -> str:
        table_name = self.table.table_name if self.table else "No Table"
        return f"Order #{self.pk} - {table_name} - {self.status}"

    def update_total(self):
        """
        Recalculates the total_amount based on all related OrderDetails.
        """
        # We define this now, but it will be useful once details are added
        total = Decimal('0.00')
        if hasattr(self, 'details'):
            for detail in self.details.all():
                total += detail.total_price
        self.total_amount = total
        self.save(update_fields=['total_amount'])
    
    def calculate_total(self) -> Decimal:
        return self.total_amount


class OrderDetail(models.Model):
    """
    Represents a specific line item within an Order.
    snapshots the price at the time of order creation.
    """
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='details',
        help_text=_("The parent order.")
    )
    
    menu_item = models.ForeignKey(
        'menu.MenuItem',
        on_delete=models.PROTECT,
        related_name='order_details',
        help_text=_("The specific dish properly ordered.")
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        help_text=_("Number of items ordered.")
    )
    
    # Item Level Status for KDS
    status = models.CharField(
        max_length=50,
        choices=Order.Status.choices,
        default=Order.Status.PENDING,
        help_text=_("Status of this specific item.")
    )
    
    # PRICE SNAPSHOT: Critical for historical data integrity
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text=_("Price per item at the moment of ordering.")
    )
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Calculated subtotal (Quantity * Unit Price).")
    )
    
    note = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Special instructions (e.g., 'No onions', 'Extra spicy').")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Order Detail")
        verbose_name_plural = _("Order Details")

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} in Order #{self.order.id}"


class Invoice(models.Model):
    """
    Represents a finalized bill for an Order.
    Table 2.11: Invoices
    """
    invoice_id = models.AutoField(primary_key=True)
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='invoice',
        help_text=_("The finalized order.")
    )
    
    issued_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when invoice was generated.")
    )
    
    final_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_("Final payable amount after taxes/discounts.")
    )
    
    payment_method = models.CharField(
        max_length=50,
        default='CASH',
        help_text=_("Primary method of payment.")
    )

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    def __str__(self):
        return f"INV-{self.invoice_id} (Order #{self.order.id})"


class Transaction(models.Model):
    """
    Logs financial transactions (payments).
    Table 2.12: Transactions
    """
    class PaymentStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')
        PENDING = 'PENDING', _('Pending')

    transaction_id = models.AutoField(primary_key=True)
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text=_("Order being paid for.")
    )
    
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text=_("Amount paid in this transaction.")
    )
    
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('CASH', 'Cash'),
            ('CARD', 'Card'),
            ('QR', 'QR Code')
        ],
        default='CASH'
    )
    
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    transaction_date = models.DateTimeField(auto_now_add=True)
    
    reference_code = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text=_("External reference (e.g., Bank Ref).")
    )

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ['-transaction_date']

    def __str__(self):
        return f"TX-{self.transaction_id}: {self.amount} ({self.status})"


