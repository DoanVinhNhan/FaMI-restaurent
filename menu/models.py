from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .services import ImageService
import uuid

class Category(models.Model):
    """
    Menu Categories (e.g., Food, Drinks, Combo).
    """
    class PrinterTarget(models.TextChoices):
        KITCHEN = 'KITCHEN', _('Kitchen')
        BAR = 'BAR', _('Bar Counter')

    name = models.CharField(max_length=100, unique=True, verbose_name=_("Category Name"))
    description = models.TextField(blank=True, null=True)
    printer_target = models.CharField(
        max_length=20, 
        choices=PrinterTarget.choices, 
        default=PrinterTarget.KITCHEN,
        verbose_name=_("Printing Target"),
        help_text=_("Where items in this category should be printed.")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """
    Individual items on the menu.
    """
    class ItemStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        INACTIVE = 'INACTIVE', _('Inactive (Hidden)')
        OUT_OF_STOCK = 'OUT_OF_STOCK', _('Out of Stock')

    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='items',
        verbose_name=_("Category")
    )
    
    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU"))
    name = models.CharField(max_length=255, verbose_name=_("Item Name"))
    description = models.TextField(blank=True, null=True)
    
    # Deprecated: "price" field is kept for backward compatibility or simple display,
    # but actual logic should prioritize Pricing model.
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Display Price"))
    
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True, verbose_name=_("Product Image"))
    
    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.ACTIVE,
        verbose_name=_("Status")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Menu Item")
        verbose_name_plural = _("Menu Items")
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_active(self):
        return self.status == self.ItemStatus.ACTIVE

    def get_current_price(self):
        """
        Retrieves the effective price for the item based on the current time.
        Returns the Pricing object or None.
        """
        now = timezone.now()
        return self.pricing_history.filter(
            effective_date__lte=now
        ).order_by('-effective_date').first()

    def save(self, *args, **kwargs):
        if self.image:
             if hasattr(self.image, 'file') and hasattr(self.image.file, 'name'):
                  try:
                      processed = ImageService.process_image(self.image)
                      if processed:
                          self.image = processed
                  except Exception:
                      pass
        super().save(*args, **kwargs)


class Pricing(models.Model):
    """
    Historical pricing for menu items.
    Allows scheduling price changes in advance.
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='pricing_history',
        verbose_name=_("Menu Item")
    )
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Selling Price"))
    effective_date = models.DateTimeField(default=timezone.now, verbose_name=_("Effective Date"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Pricing")
        verbose_name_plural = _("Pricing History")
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['menu_item', 'effective_date']),
        ]

    def __str__(self):
        return f"{self.menu_item.name} - {self.selling_price} ({self.effective_date})"


# --- Recipe / BOM Models ---

class Recipe(models.Model):
    """
    Represents the production formula (BOM) for a Menu Item.
    One Menu Item typically has one standard Recipe.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item = models.OneToOneField(
        'menu.MenuItem',
        on_delete=models.CASCADE, 
        related_name='recipe',
        verbose_name=_("Menu Item")
    )
    instructions = models.TextField(
        blank=True, 
        null=True, 
        verbose_name=_("Preparation Instructions")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Recipe")
        verbose_name_plural = _("Recipes")

    def __str__(self) -> str:
        return f"Recipe for {self.menu_item}"

    def calculate_standard_cost(self) -> float:
        """
        Calculates the theoretical cost of this recipe based on ingredients.
        """
        total_cost = 0.0
        for item in self.ingredients.all():
            if hasattr(item.ingredient, 'cost_per_unit'):
                cost = float(item.ingredient.cost_per_unit) * float(item.quantity)
                total_cost += cost
        return total_cost


class RecipeIngredient(models.Model):
    """
    Intermediate model linking a Recipe to an Ingredient (Many-to-Many).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(
        Recipe, 
        on_delete=models.CASCADE, 
        related_name='ingredients',
        verbose_name=_("Recipe")
    )
    # String reference to Inventory App
    ingredient = models.ForeignKey(
        'inventory.Ingredient', 
        on_delete=models.PROTECT, 
        related_name='used_in_recipes',
        verbose_name=_("Ingredient")
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        help_text=_("Quantity used per unit of the menu item"),
        verbose_name=_("Quantity")
    )
    unit = models.CharField(
        max_length=50, 
        verbose_name=_("Unit"),
        help_text=_("Unit of measurement for this recipe (e.g., grams, ml)")
    )

    class Meta:
        verbose_name = _("Recipe Ingredient")
        verbose_name_plural = _("Recipe Ingredients")
        unique_together = ('recipe', 'ingredient')

    def __str__(self) -> str:
        return f"{self.ingredient} x {self.quantity} {self.unit}"
