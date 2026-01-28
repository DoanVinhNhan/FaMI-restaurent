from django.test import TestCase
from decimal import Decimal

from menu.models import MenuItem, Category, Recipe, RecipeIngredient
from inventory.models import Ingredient, InventoryItem


class InventorySignalsTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Food')
        self.item = MenuItem.objects.create(sku='S-01', name='Test Item', price=10, category=self.category, status=MenuItem.ItemStatus.ACTIVE)
        self.ing = Ingredient.objects.create(name='Beef', cost_per_unit=10, unit='kg')
        self.inv = InventoryItem.objects.create(ingredient=self.ing, quantity_on_hand=Decimal('1.0'))
        self.recipe = Recipe.objects.create(menu_item=self.item)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.ing, quantity=Decimal('0.5'), unit='kg')

    def test_item_marked_out_of_stock_when_inventory_zero(self):
        self.inv.quantity_on_hand = Decimal('0.0')
        self.inv.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, MenuItem.ItemStatus.OUT_OF_STOCK)

    def test_item_reactivated_when_inventory_replenished(self):
        # First make it OOS
        self.inv.quantity_on_hand = Decimal('0.0')
        self.inv.save()
        # Now replenish
        self.inv.quantity_on_hand = Decimal('10.0')
        self.inv.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, MenuItem.ItemStatus.ACTIVE)
