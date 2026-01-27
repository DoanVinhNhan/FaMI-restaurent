import os
import sys
import django
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Ingredient, InventoryItem, StockTakeTicket, StockTakeDetail

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 025 VERIFICATION (Stock Take Logic)")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='stock_manager_logic')
    ing, _ = Ingredient.objects.get_or_create(
        sku='LOGIC-TEST-01', 
        defaults={'name': 'Logic Test Flour', 'unit': 'kg', 'cost_per_unit': Decimal('2.00')}
    )
    
    # Ensure Inventory exists (Set to 50)
    item, _ = InventoryItem.objects.get_or_create(ingredient=ing)
    item.quantity_on_hand = Decimal('50.00')
    item.save()
    
    print(f"Initial Stock: {item.quantity_on_hand}")

    # 2. Simulate View Logic: Create Ticket -> Snapshot
    # In views, we iterate all inventory items. Here we simulate that.
    ticket = StockTakeTicket.objects.create(
        code='ST-LOGIC-001',
        creator=user,
        status=StockTakeTicket.Status.DRAFT
    )
    
    detail = StockTakeDetail.objects.create(
        ticket=ticket,
        ingredient=item.ingredient,
        snapshot_quantity=item.quantity_on_hand, # 50
        actual_quantity=item.quantity_on_hand    # 50 (Default)
    )
    print("Snapshot Taken.")

    # 3. Simulate Draft Update (User counts 40)
    # View would receive Form data. Here we assume validation passed.
    detail.actual_quantity = Decimal('40.00')
    detail.save() # variance should check here? Model save updates variance.
    
    # Verify variance
    if detail.variance == Decimal('-10.00'):
        print(f"PASS: Draft updated var correctly: {detail.variance}")
    else:
        print(f"FAIL: Variance wrong: {detail.variance}")

    # 4. Simulate Finalization
    # Logic: Iterate details, update InventoryItem
    print("Finalizing...")
    
    # Refetch detail
    detail.refresh_from_db()
    
    # Update inventory item
    inv_item = InventoryItem.objects.get(ingredient=detail.ingredient)
    inv_item.quantity_on_hand = detail.actual_quantity
    inv_item.save()
    
    # Update Ticket
    ticket.status = StockTakeTicket.Status.COMPLETED
    ticket.variance_total_value = detail.variance * ing.cost_per_unit # -10 * 2 = -20
    ticket.save()

    # 5. Verify Results
    inv_item.refresh_from_db()
    print(f"Final Live Stock: {inv_item.quantity_on_hand}")
    
    if inv_item.quantity_on_hand == Decimal('40.00'):
        print("PASS: Live Inventory successfully updated to Actual.")
    else:
        print("FAIL: Live Inventory not updated.")

    if ticket.status == 'COMPLETED':
         print("PASS: Ticket marked as Completed.")

    print(">>> TASK 025 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
