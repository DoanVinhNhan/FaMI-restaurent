from django.contrib import admin
from .models import Ingredient, InventoryItem

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Admin view for managing Ingredient master data."""
    list_display = ('id', 'sku', 'name', 'unit', 'cost_per_unit', 'alert_threshold')
    search_fields = ('sku', 'name')
    list_filter = ('unit',)
    ordering = ('name',)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """Admin view for managing Stock levels."""
    list_display = ('ingredient_name', 'quantity_on_hand', 'ingredient_unit', 'storage_location', 'is_low_stock_status')
    search_fields = ('ingredient__name', 'ingredient__sku', 'storage_location')
    
    def ingredient_name(self, obj) -> str:
        return obj.ingredient.name
    ingredient_name.short_description = "Ingredient"

    def ingredient_unit(self, obj) -> str:
        return obj.ingredient.unit
    ingredient_unit.short_description = "Unit"

    def is_low_stock_status(self, obj) -> bool:
        return obj.is_low_stock()
    is_low_stock_status.boolean = True
    is_low_stock_status.short_description = "Low Stock?"


# --- Task 024 Extensions ---
from .models import StockTakeTicket, StockTakeDetail

class StockTakeDetailInline(admin.TabularInline):
    model = StockTakeDetail
    extra = 0
    readonly_fields = ('variance',)
    fields = ('ingredient', 'snapshot_quantity', 'actual_quantity', 'variance', 'reason')

@admin.register(StockTakeTicket)
class StockTakeTicketAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_at', 'creator', 'status', 'variance_total_value')
    list_filter = ('status', 'created_at')
    inlines = [StockTakeDetailInline]
