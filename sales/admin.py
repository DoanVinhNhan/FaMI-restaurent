from django.contrib import admin
from .models import RestaurantTable

@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ('table_name', 'capacity', 'status', 'updated_at')
    list_filter = ('status', 'capacity')
    search_fields = ('table_name',)
    ordering = ('table_name',)

# --- Promotion Admin ---
from .models import Promotion, PromotionDetail

class PromotionDetailInline(admin.TabularInline):
    model = PromotionDetail
    extra = 1

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'promo_code', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active',)
    search_fields = ('name', 'promo_code')
    inlines = [PromotionDetailInline]

# --- Order Admin ---
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'table', 
        'user', 
        'total_amount', 
        'status', 
        'created_at'
    )
    list_filter = ('status', 'created_at', 'table')
    search_fields = ('id', 'user__username', 'table__table_name')

# --- OrderDetail Admin ---
from .models import OrderDetail

class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 1
    readonly_fields = ('unit_price', 'total_price') 
    fields = ('menu_item', 'quantity', 'note', 'unit_price', 'total_price')

@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'unit_price', 'total_price', 'created_at')
    readonly_fields = ('unit_price', 'total_price')
