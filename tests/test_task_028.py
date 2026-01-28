
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.request import Request
from decimal import Decimal

from inventory.models import Ingredient, InventoryItem
from menu.models import MenuItem, Category
from sales.models import Order
from inventory.serializers import InventoryItemSerializer
from menu.serializers import MenuItemSerializer
from sales.serializers import OrderSerializer

User = get_user_model()

class SerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_user', password='password')
        self.category = Category.objects.create(name="FoodAPI")
        self.item = MenuItem.objects.create(name="BurgerAPI", price=Decimal('55000.00'), category=self.category, sku="API01")
        
        self.ingredient = Ingredient.objects.create(sku='ING01', name='Meat', unit='kg', cost_per_unit=100)
        self.inv_item = InventoryItem.objects.create(ingredient=self.ingredient, quantity_on_hand=100)
        
        self.factory = RequestFactory()

    def test_inventory_serialization(self):
        serializer = InventoryItemSerializer(self.inv_item)
        data = serializer.data
        self.assertEqual(data['ingredient_sku'], 'ING01')
        print("PASS: Inventory Serializer")

    def test_menu_serialization(self):
        serializer = MenuItemSerializer(self.item)
        data = serializer.data
        self.assertEqual(data['name'], "BurgerAPI")
        self.assertEqual(str(data['price']), "55000.00")
        print("PASS: Menu Serializer")

    def test_order_creation_serializer(self):
        # Simulate POST payload
        payload = {
            'items_payload': [
                {'menu_item_id': self.item.id, 'quantity': 2, 'note': 'No onion'}
            ]
        }
        
        # DRF requires request context for finding user in create() method if we used self.context['request'].user
        # We need to mock that context
        request = self.factory.post('/api/orders/', payload, content_type='application/json')
        request.user = self.user
        drf_request = Request(request)
        
        serializer = OrderSerializer(data=payload, context={'request': drf_request})
        if serializer.is_valid():
            order = serializer.save()
            print(f"PASS: Order Created via Serializer: ID {order.id}")
            print(f"PASS: Order Total: {order.total_amount}")
            
            self.assertEqual(order.total_amount, Decimal('110000.00')) # 55k * 2
            self.assertEqual(order.user, self.user)
            self.assertEqual(order.details.count(), 1)
        else:
            print(f"FAIL: Serializer Errors: {serializer.errors}")
            self.fail("Serializer validation failed")

