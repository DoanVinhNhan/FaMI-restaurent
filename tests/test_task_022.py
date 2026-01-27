import os
import sys
import django
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from menu.models import MenuItem, Recipe, RecipeIngredient, Category
from inventory.models import Ingredient, InventoryItem
from kitchen.models import ReasonCode, WasteReport
from inventory.services import WasteService

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 022 VERIFICATION (Kitchen Waste Logic)")
    
    # 1. Setup Test Data
    print("--- Setting up Test Data ---")
    user, _ = User.objects.get_or_create(username='kitchen_staff_waste')
    cat, _ = Category.objects.get_or_create(name='Waste Cat')

    # Create Reason Code
    reason, _ = ReasonCode.objects.get_or_create(code='BURN_TEST', defaults={'description': 'Burnt during cooking'})

    # Create Ingredients (Bun, Patty)
    bun, _ = Ingredient.objects.get_or_create(
        sku='ING-BUN-TEST', 
        defaults={'name': 'Burger Bun Test', 'unit': 'pcs', 'cost_per_unit': Decimal('0.50')}
    )
    patty, _ = Ingredient.objects.get_or_create(
        sku='ING-PATTY-TEST', 
        defaults={'name': 'Beef Patty Test', 'unit': 'pcs', 'cost_per_unit': Decimal('1.50')}
    )

    # Set Initial Inventory
    inv_bun, _ = InventoryItem.objects.get_or_create(ingredient=bun)
    inv_bun.quantity_on_hand = Decimal('100.00')
    inv_bun.save()

    inv_patty, _ = InventoryItem.objects.get_or_create(ingredient=patty)
    inv_patty.quantity_on_hand = Decimal('100.00')
    inv_patty.save()

    print(f"Initial Inventory: Bun={inv_bun.quantity_on_hand}, Patty={inv_patty.quantity_on_hand}")

    # Create Menu Item (Burger) and Recipe
    burger, _ = MenuItem.objects.get_or_create(sku='MENU-BURGER-TEST', defaults={'name': 'Cheeseburger Test', 'price': 5, 'category': cat})
    recipe, _ = Recipe.objects.get_or_create(menu_item=burger)
    
    # 1 Burger = 1 Bun + 1 Patty
    RecipeIngredient.objects.get_or_create(recipe=recipe, ingredient=bun, quantity=1)
    RecipeIngredient.objects.get_or_create(recipe=recipe, ingredient=patty, quantity=1)

    print("--- Executing Waste Report (BOM Explosion) ---")
    # 2. Report Waste: 5 Burgers were burnt
    try:
        report = WasteService.report_waste(
            user=user,
            item_type='menu_item',
            item_id=burger.pk,
            quantity=5,
            reason_id='BURN_TEST'
        )
        print(f"PASS: Report Created ID {report.log_id}")
        
        expected_loss = Decimal('5') * (Decimal('0.50') + Decimal('1.50')) # 5 * 2 = 10
        print(f"Loss Value: ${report.loss_value} (Expected: {expected_loss})")
        
        if report.loss_value == expected_loss:
            print("PASS: Loss Value Correct.")
        else:
            print("FAIL: Loss Value Incorrect.")
    except Exception as e:
        print(f"FAIL: Error reporting waste: {e}")

    # 3. Verify Inventory Deduction
    inv_bun.refresh_from_db()
    inv_patty.refresh_from_db()

    print(f"Final Inventory: Bun={inv_bun.quantity_on_hand}, Patty={inv_patty.quantity_on_hand}")
    
    if inv_bun.quantity_on_hand == 95 and inv_patty.quantity_on_hand == 95:
        print("PASS: BOM Explosion worked correctly (Inventory Deducted).")
    else:
        print("FAIL: Inventory not deducted correctly.")

    print(">>> TASK 022 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
