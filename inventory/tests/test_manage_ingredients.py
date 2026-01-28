from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from inventory.models import Ingredient, InventoryItem
from menu.models import Recipe, MenuItem, RecipeIngredient, Category
from inventory.views import IngredientDeleteView, IngredientListView

User = get_user_model()

class ManageIngredientsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username='admin', password='password')
        
        self.ingredient = Ingredient.objects.create(
            sku='ING-001', name='Rice', unit='kg', cost_per_unit=10
        )
        # Ensure inventory item created
        self.inv_item, _ = InventoryItem.objects.get_or_create(ingredient=self.ingredient)

    def test_search_ingredient(self):
        # Create another ingredient
        Ingredient.objects.create(sku='ING-002', name='Noodle', unit='kg')
        
        url = reverse('inventory:ingredient_list')
        self.client.force_login(self.user)
        response = self.client.get(url, {'q': 'Rice'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ingredients']), 1)
        self.assertEqual(response.context['ingredients'][0].name, 'Rice')

    def test_delete_protected_by_stock(self):
        # Set stock > 0
        self.inv_item.quantity_on_hand = 10
        self.inv_item.save()
        
        url = reverse('inventory:ingredient_delete', args=[self.ingredient.pk])
        self.client.force_login(self.user)
        response = self.client.post(url)
        
        # Should redirect with error (302)
        self.assertEqual(response.status_code, 302)
        # Verify not deleted
        self.assertTrue(Ingredient.objects.filter(pk=self.ingredient.pk).exists())

    def test_delete_protected_by_recipe(self):
        self.inv_item.quantity_on_hand = 0
        self.inv_item.save()
        
        # Link to recipe
        cat = Category.objects.create(name='Food')
        menu = MenuItem.objects.create(name='Rice Dish', price=10, category=cat)
        recipe = Recipe.objects.create(menu_item=menu)
        RecipeIngredient.objects.create(recipe=recipe, ingredient=self.ingredient, quantity=1, unit='kg')
        
        url = reverse('inventory:ingredient_delete', args=[self.ingredient.pk])
        self.client.force_login(self.user)
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ingredient.objects.filter(pk=self.ingredient.pk).exists())

    def test_delete_success(self):
        self.inv_item.quantity_on_hand = 0
        self.inv_item.save()
        
        # Ensure not in recipe (clean state from setUp)
        
        url = reverse('inventory:ingredient_delete', args=[self.ingredient.pk])
        self.client.force_login(self.user)
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Ingredient.objects.filter(pk=self.ingredient.pk).exists())
