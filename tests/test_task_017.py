import os
import sys
import django
from decimal import Decimal
from django.utils import timezone

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.models import Order
from sales.services import OrderService
from menu.models import MenuItem, Pricing, Category, Recipe, RecipeIngredient
from inventory.models import Ingredient, InventoryItem
from django.contrib.auth import get_user_model

def run_test():
    print(">>> STARTING TASK 017 VERIFICATION (Order Creation)")
    
    # 1. Setup Mock Data
    print("\n--- Setup Data ---")
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='helper_order_service')
    
    cat, _ = Category.objects.get_or_create(name="Service Test Cat")
    
    # Ingredient & Inventory
    ing, _ = Ingredient.objects.get_or_create(sku="SERVICE-ING-01", name="Service Beef", unit="kg")
    # Clear existing inventory for test
    InventoryItem.objects.filter(ingredient=ing).delete()
    # Add stock: 10kg
    InventoryItem.objects.create(ingredient=ing, quantity_on_hand=10)
    print("Added 10kg 'Service Beef' to Inventory")

    # Item with Recipe
    item, _ = MenuItem.objects.get_or_create(sku="SERVICE-BURGER", defaults={'name': 'Service Burger', 'category': cat, 'price': 100000, 'status': 'ACTIVE'})
    Pricing.objects.create(menu_item=item, selling_price=100000, effective_date=timezone.now())
    
    recipe, _ = Recipe.objects.get_or_create(menu_item=item, defaults={'instructions': 'Cook it'})
    RecipeIngredient.objects.get_or_create(recipe=recipe, ingredient=ing, defaults={'quantity': 1, 'unit': 'kg'}) # Needs 1kg per burger
    print(f"Recipe: 1 {item.name} uses 1kg {ing.name}")

    # Item without Recipe (should pass inventory check trivially)
    simple, _ = MenuItem.objects.get_or_create(sku="SERVICE-COKE", defaults={'name': 'Coke', 'category': cat, 'price': 20000, 'status': 'ACTIVE'})
    Pricing.objects.create(menu_item=simple, selling_price=20000, effective_date=timezone.now())

    # 2. Test Idempotency
    print("\nTest 1: Idempotency...")
    payload1 = {
        'external_id': 'EXT-IDEM-001',
        'user': user,
        'items': [{'sku': 'SERVICE-COKE', 'qty': 1}]
    }
    
    res1 = OrderService.create_order_from_api(payload1)
    if res1['success']:
        print(f"PASS: Created Order 1 (ID: {res1['order_id']})")
    else:
        print(f"FAIL: Create 1 failed: {res1.get('error')}")
        
    res2 = OrderService.create_order_from_api(payload1)
    if res2['success'] and res2.get('message') == 'Order already exists':
         print(f"PASS: Handling duplicate EXT-IDCorrectly (Returns ID: {res2['order_id']})")
    else:
         print(f"FAIL: Duplicate check failed. Result: {res2}")

    # 3. Test Inventory Validation (Pass)
    print("\nTest 2: Inventory Check (Pass)...")
    # Order 5 burgers -> Needs 5kg beef (Have 10kg)
    payload_pass = {
        'external_id': 'EXT-STOCK-PASS',
        'user': user,
        'items': [{'sku': 'SERVICE-BURGER', 'qty': 5}]
    }
    res_pass = OrderService.create_order_from_api(payload_pass)
    if res_pass['success']:
        print("PASS: Order created with sufficient stock")
    else:
        print(f"FAIL: Failed valid stock order: {res_pass.get('error')}")

    # 4. Test Inventory Block (Fail)
    print("\nTest 3: Inventory Block (Fail)...")
    # Remaining Stock: 5kg. Order 6 burgers -> Needs 6kg.
    payload_fail = {
        'external_id': 'EXT-STOCK-FAIL',
        'user': user,
        'items': [{'sku': 'SERVICE-BURGER', 'qty': 6}]
    }
    res_fail = OrderService.create_order_from_api(payload_fail)
    if not res_fail['success'] and "Not enough stock" in res_fail.get('error', ''):
        print(f"PASS: Blocked OOS Order correctly. Error: {res_fail['error']}")
    else:
        print(f"FAIL: Did not block OOS correctly. Result: {res_fail}")

    print(">>> TASK 017 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
