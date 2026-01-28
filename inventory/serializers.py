from rest_framework import serializers
from .models import Ingredient, InventoryItem, StockTakeTicket, StockTakeDetail

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'sku', 'name', 'unit', 'cost_per_unit', 'alert_threshold']

class InventoryItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_sku = serializers.CharField(source='ingredient.sku', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model = InventoryItem
        fields = ['ingredient', 'ingredient_name', 'ingredient_sku', 'ingredient_unit', 'quantity_on_hand', 'storage_location']
