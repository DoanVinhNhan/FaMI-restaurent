import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings') # Ensure 'core' matches your project folder name
django.setup()

from inventory.models import Ingredient, InventoryItem
from django.db.utils import IntegrityError
import decimal

def run_verification():
    print("--- Starting Inventory Verification ---")
    
    # Clean up previous runs
    InventoryItem.objects.all().delete()
    Ingredient.objects.all().delete()

    # 1. Create an Ingredient
    try:
        flour = Ingredient.objects.create(
            sku="ING-001",
            name="Wheat Flour",
            unit="kg",
            cost_per_unit=1.50,
            alert_threshold=10
        )
        print(f"✅ Created Ingredient: {flour}")
    except Exception as e:
        print(f"❌ Failed to create Ingredient: {e}")
        return

    # 2. Create associated Inventory Item
    try:
        flour_stock = InventoryItem.objects.create(
            ingredient=flour,
            quantity_on_hand=50.00,
            storage_location="Shelf A1"
        )
        print(f"✅ Created InventoryItem: {flour_stock}")
    except Exception as e:
        print(f"❌ Failed to create InventoryItem: {e}")
        return

    # 3. Verify Relationship Access
    fetched_stock = InventoryItem.objects.get(ingredient__sku="ING-001")
    if fetched_stock.ingredient.name == "Wheat Flour":
        print(f"✅ Relationship verified: Stock points to {fetched_stock.ingredient.name}")
    else:
        print(f"❌ Relationship check failed")

    # 4. Test Low Stock Logic
    # Threshold is 10, Qty is 50 -> Should be False
    if not flour_stock.is_low_stock():
        print(f"✅ Low stock check passed (50 > 10)")
    else:
        print(f"❌ Low stock check failed")

    # Update to low stock
    flour_stock.quantity_on_hand = 5.00
    flour_stock.save()
    
    if flour_stock.is_low_stock():
        print(f"✅ Low stock alert triggered (5 <= 10)")
    else:
        print(f"❌ Low stock alert failed")

    # 5. Verify Constraints (Unique SKU)
    try:
        Ingredient.objects.create(
            sku="ING-001", # Duplicate SKU
            name="Another Flour"
        )
        print("❌ Constraint failed: Allowed duplicate SKU")
    except IntegrityError:
        print("✅ Constraint verified: Blocked duplicate SKU")

    print("--- Verification Complete ---")

if __name__ == "__main__":
    run_verification()
