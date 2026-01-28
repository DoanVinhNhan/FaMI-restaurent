from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from menu.models import MenuItem, Category
from inventory.models import Ingredient, InventoryItem
from menu.models import Recipe, RecipeIngredient

User = get_user_model()

class POSOutOfStockDisplayTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cashier', password='pass')
        self.client.force_login(self.user)
        self.table = 1
        self.cat = Category.objects.create(name='Food')

        # Create menu item with recipe -> so availability depends on inventory
        self.item = MenuItem.objects.create(sku='POS-01', name='POS Item', price=10, category=self.cat, status=MenuItem.ItemStatus.ACTIVE)
        self.ing = Ingredient.objects.create(name='Rice', cost_per_unit=1, unit='kg')
        self.inv = InventoryItem.objects.create(ingredient=self.ing, quantity_on_hand=Decimal('1.0'))
        self.recipe = Recipe.objects.create(menu_item=self.item)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.ing, quantity=Decimal('0.5'), unit='kg')

    def test_oos_item_is_shown_but_disabled_on_pos(self):
        # Make inventory zero -> should mark item OUT_OF_STOCK via signals
        self.inv.quantity_on_hand = Decimal('0.0')
        self.inv.save()

        url = reverse('sales:pos_table_detail', args=[self.table])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode('utf-8')
        # Item should appear on the page
        self.assertIn('POS Item', content)
        # The disabled badge text should be present
        self.assertIn('ĐÃ HẾT', content)
        # Card should include opacity or pointer-events none (disabled style)
        self.assertIn('opacity-50', content)
        self.assertIn('pointer-events: none', content)
