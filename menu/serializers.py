from rest_framework import serializers
from .models import Category, MenuItem, Pricing
from sales.models import Promotion

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'printer_target', 'is_active']

class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = ['selling_price', 'effective_date']

class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = ['id', 'sku', 'name', 'description', 'price', 'category', 'category_name', 'image', 'status', 'current_price']

    def get_current_price(self, obj):
        pricing = obj.get_current_price()
        if pricing:
            return pricing.selling_price
        return obj.price # Fallback to display price

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'promo_code', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active']
