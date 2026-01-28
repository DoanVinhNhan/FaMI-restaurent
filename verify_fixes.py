
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import SystemSetting
from inventory.models import Ingredient, InventoryItem
from menu.models import Category, MenuItem, Recipe, RecipeIngredient, Pricing
from sales.models import RestaurantTable, Order, OrderDetail
from inventory.services import InventoryService
from django.test import RequestFactory

User = get_user_model()

def verify_fixes():
    print("=== Verifying Fixes ===")

    # 1. Verify User Password Field (Task 12)
    # Check if we can create user with password via form essentially (or just model logic)
    print("\n[Check] User Model & Password:")
    try:
        user = User.objects.create_user(username='test_user_pw', password='newpassword123', role='CASHIER')
        print(f"  OK: Created user {user.username} with password.")
        if not user.check_password('newpassword123'):
             print("  FAIL: Password check failed.")
        else:
             print("  OK: Password verified.")
    except Exception as e:
        print(f"  FAIL: {e}")

    # 2. Verify Menu Item Fields (Task 11)
    print("\n[Check] Menu Item New Fields (prep_time, is_popular):")
    try:
        cat = Category.objects.first()
        if not cat:
            cat = Category.objects.create(name="Test Cat")
        
        item = MenuItem.objects.create(
            sku="TEST-MENU-01",
            name="Test Dish",
            category=cat,
            price=10000,
            prep_time=15,
            is_popular=True
        )
        item.refresh_from_db()
        if item.prep_time == 15 and item.is_popular:
            print("  OK: Fields saved correctly.")
        else:
            print(f"  FAIL: Fields mismatch. prep_time={item.prep_time}, is_popular={item.is_popular}")
    except Exception as e:
        print(f"  FAIL: {e}")

    # 3. Verify Inventory Service Fix (Task 7 & 9)
    print("\n[Check] Inventory Logic (deduct_ingredients_for_order):")
    try:
        # Require an Ingredient and Recipe
        ing = Ingredient.objects.create(sku='ING-TEST', name='Test Ing', unit='kg', cost_per_unit=100)
        inv_item, _ = InventoryItem.objects.get_or_create(ingredient=ing, defaults={'quantity_on_hand': 100})
        inv_item.quantity_on_hand = 100
        inv_item.save()
        
        # Link to Menu Item
        Recipe.objects.filter(menu_item=item).delete()
        recipe = Recipe.objects.create(menu_item=item)
        RecipeIngredient.objects.create(recipe=recipe, ingredient=ing, quantity=1, unit='kg')
        
        # Create Order
        table = RestaurantTable.objects.first() or RestaurantTable.objects.create(table_name="Test Table")
        order = Order.objects.create(table=table, user=user, status=Order.Status.COOKING)
        OrderDetail.objects.create(order=order, menu_item=item, quantity=2, unit_price=10000, total_price=20000)
        
        # Run Logic
        InventoryService.deduct_ingredients_for_order(order)
        
        # Check Inventory
        inv_item.refresh_from_db()
        # Needed: 2 items * 1 kg = 2kg deduction. 100 - 2 = 98.
        if inv_item.quantity_on_hand == 98:
            print("  OK: Inventory deducted correctly (100 -> 98).")
        else:
            print(f"  FAIL: Inventory mismatch. Expected 98, Got {inv_item.quantity_on_hand}")
            
    except AttributeError:
        print("  FAIL: Attribute Error! Did you rename the method?")
    except Exception as e:
        print(f"  FAIL: {e}")
        
    # 4. Verify Fast Food Seed Data (Task 5)
    print("\n[Check] Seed Data Content:")
    if MenuItem.objects.filter(name__icontains="Gà Rán").exists():
        print("  OK: Found 'Gà Rán' (Fast Food Item).")
    else:
        print("  FAIL: 'Gà Rán' not found. Seed data might be wrong.")

    if MenuItem.objects.filter(name__icontains="Phở").exists():
        print("  FAIL: Found 'Phở'. Seed data clean failed?")
    else:
        print("  OK: 'Phở' not found (Cleaned correctly).")

if __name__ == '__main__':
    verify_fixes()
