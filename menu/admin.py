from django.contrib import admin
from .models import Category, MenuItem, Pricing

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'printer_target', 'is_active')
    list_filter = ('printer_target', 'is_active')
    search_fields = ('name',)

class PricingInline(admin.TabularInline):
    model = Pricing
    extra = 1
    fields = ('selling_price', 'effective_date')
    ordering = ('-effective_date',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'current_price_display', 'status', 'is_active_display')
    list_filter = ('status', 'category')
    search_fields = ('sku', 'name')
    list_editable = ('status',)
    inlines = [PricingInline]
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = "Is Active?"

    def current_price_display(self, obj):
        pricing = obj.get_current_price()
        if pricing:
            return pricing.selling_price
        return obj.price # Fallback to display price if no pricing history
    current_price_display.short_description = "Current Price"

@admin.register(Pricing)
class PricingAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'selling_price', 'effective_date')
    list_filter = ('effective_date',)
    search_fields = ('menu_item__name', 'menu_item__sku')

# --- Recipe Admin ---
from .models import Recipe, RecipeIngredient

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'ingredient_count', 'updated_at')
    search_fields = ('menu_item__name', 'menu_item__sku')
    inlines = [RecipeIngredientInline]

    def ingredient_count(self, obj):
        return obj.ingredients.count()
    ingredient_count.short_description = "Ingredients"
