from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from decimal import Decimal

from core.models import SystemSetting, SettingGroup
from menu.models import MenuItem, Category
from sales.models import Order
from inventory.models import Ingredient, InventoryItem
from menu.models import Recipe, RecipeIngredient

User = get_user_model()

class CreateThirdPartyOrderViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('sales:api_create_order') # Ensure this matches urls.py

        # 1. Setup User
        self.user = User.objects.create_superuser(username='admin', password='password')

        # 2. Setup Restaurant Status -> OPEN
        group, _ = SettingGroup.objects.get_or_create(group_name='General')
        SystemSetting.objects.create(
            setting_key='RESTAURANT_STATUS',
            setting_value='OPEN',
            group=group
        )

        # 3. Setup Menu Item
        self.category = Category.objects.create(name='Food')
        self.item = MenuItem.objects.create(
            sku='ITEM-001',
            name='Burger',
            price=Decimal('100.00'),
            category=self.category,
            status='ACTIVE'
        )

        # 4. Setup Inventory (Simple no recipe = always available, or add recipe)
        # Let's add a recipe to test stock check properly
        self.ingredient = Ingredient.objects.create(name='Beef', cost_per_unit=10, unit='kg')
        self.inv_item = InventoryItem.objects.create(ingredient=self.ingredient, quantity_on_hand=100) # Plenty
        
        self.recipe = Recipe.objects.create(menu_item=self.item)
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=Decimal('0.1'), # 0.1kg per burger
            unit='kg'
        )

    def test_create_order_success(self):
        payload = {
            "partner_order_id": "ORD-001",
            "items": [
                {"sku": "ITEM-001", "quantity": 2, "price": 100.00}
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Order.Status.COOKING)
        self.assertTrue(Order.objects.filter(external_id="ORD-001").exists())

    def test_restaurant_closed(self):
        # Close the restaurant
        setting = SystemSetting.objects.get(setting_key='RESTAURANT_STATUS')
        setting.setting_value = 'CLOSED'
        setting.save()

        payload = {
            "partner_order_id": "ORD-002",
            "items": [{"sku": "ITEM-001", "quantity": 1}]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_out_of_stock(self):
        # Set inventory to 0
        self.inv_item.quantity_on_hand = 0
        self.inv_item.save()

        payload = {
            "partner_order_id": "ORD-003",
            "items": [{"sku": "ITEM-001", "quantity": 1}]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('unavailable_items', response.data)
        self.assertEqual(response.data['unavailable_items'][0]['ITEM-001'], 'Out of Stock')

    def test_price_mismatch_warning(self):
        # Incoming price 120 (Database is 100). Diff 20 > 5% (5).
        payload = {
            "partner_order_id": "ORD-004",
            "items": [
                {"sku": "ITEM-001", "quantity": 1, "price": 120.00} 
            ]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Order.Status.PENDING) # Should be Pending Manual Review

        self.assertIn('warning', response.data)
