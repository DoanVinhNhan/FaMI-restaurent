import os
import sys
import django
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.models import Order, RestaurantTable
from django.contrib.auth import get_user_model

def run_test():
    print(">>> STARTING TASK 015 VERIFICATION (Order Model)")
    
    # Setup
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='helper_order_test')
    table, _ = RestaurantTable.objects.get_or_create(table_name="T-ORDER", capacity=4)
    
    # 1. Create Basic Order
    print("\nTest 1: Create Basic Order...")
    order = Order.objects.create(
        user=user,
        table=table
    )
    print(f"PASS: Created {order}")
    
    # Verify Defaults
    if order.status == Order.Status.PENDING:
        print("PASS: Status defaults to Pending")
    else:
        print(f"FAIL: Status is {order.status}")
        
    if order.total_amount == Decimal('0.00'):
        print("PASS: Total amount defaults to 0.00")
    else:
        print(f"FAIL: Total amount is {order.total_amount}")

    # 2. Verify Table Relation
    print("\nTest 2: Table Relation...")
    if order.table == table:
        print(f"PASS: Order linked to table {table.table_name}")
    else:
        print("FAIL: Order not linked to table")

    # 3. Test update_total (Placeholder functionality)
    print("\nTest 3: update_total()...")
    # Should stay 0.00 as no details exist
    order.update_total()
    if order.total_amount == Decimal('0.00'):
        print("PASS: update_total handled empty details correctly")
    else:
         print(f"FAIL: update_total changed amount unexpectedly to {order.total_amount}")

    print(">>> TASK 015 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
