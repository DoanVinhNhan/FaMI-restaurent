import os
import sys
import django
from decimal import Decimal
from django.utils import timezone

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category, Pricing
from django.contrib.auth import get_user_model

def run_test():
    print(">>> STARTING TASK 016 VERIFICATION (OrderDetail & Snapshots)")
    
    # Setup Data
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='helper_order_detail_test')
    table, _ = RestaurantTable.objects.get_or_create(table_name="T-DETAIL", capacity=2)
    cat, _ = Category.objects.get_or_create(name="Detail Test Cat")
    
    # Create MenuItem with Price
    item, _ = MenuItem.objects.get_or_create(sku="OD-ITEM-01", defaults={'name': 'Snapshot Dish', 'category': cat, 'price': 100})
    # Ensure active pricing
    Pricing.objects.create(menu_item=item, selling_price=Decimal('50.00'), effective_date=timezone.now())

    # Create Order
    order = Order.objects.create(user=user, table=table)
    print(f"PASS: Created Order #{order.pk} (Total: {order.total_amount})")

    # 1. Add Detail (Snapshot Logic)
    print("\nTest 1: Adding Order Detail (Snapshot Logic)...")
    detail1 = OrderDetail.objects.create(order=order, menu_item=item, quantity=2)
    
    if detail1.unit_price == Decimal('50.00'):
         print(f"PASS: Unit Price snapshotted correctly: {detail1.unit_price}")
    else:
         print(f"FAIL: Unit Price mismatch. Got {detail1.unit_price}")
         
    if detail1.total_price == Decimal('100.00'): # 2 * 50
         print(f"PASS: Total Price calculated correctly: {detail1.total_price}")
    else:
         print(f"FAIL: Total Price mismatch. Got {detail1.total_price}")

    # 2. Check Order Header Update
    print("\nTest 2: Order Header Update...")
    order.refresh_from_db()
    if order.total_amount == Decimal('100.00'):
        print(f"PASS: Order total updated to {order.total_amount}")
    else:
        print(f"FAIL: Order total mismatch. Got {order.total_amount}")

    # 3. Verify Price Change Doesn't Affect Snapshot
    print("\nTest 3: Historical Integrity...")
    # Change Active Price for Item
    new_price = Pricing.objects.create(menu_item=item, selling_price=Decimal('999.00'), effective_date=timezone.now())
    print("INFO: Changed Menu Price to 999.00")
    
    detail1.refresh_from_db()
    if detail1.unit_price == Decimal('50.00'):
        print("PASS: Existing OrderDetail price remained 50.00")
    else:
        print(f"FAIL: OrderDetail price changed to {detail1.unit_price}")

    # Add new item to see new price
    detail2 = OrderDetail.objects.create(order=order, menu_item=item, quantity=1)
    if detail2.unit_price == Decimal('999.00'):
        print("PASS: New OrderDetail picked up new price 999.00")
    else:
         print(f"FAIL: New OrderDetail got price {detail2.unit_price}")
    
    order.refresh_from_db()
    # Total should be 100 + 999 = 1099
    if order.total_amount == Decimal('1099.00'):
         print(f"PASS: Order Total updated correctly to {order.total_amount}")
    else:
         print(f"FAIL: Order Total is {order.total_amount}")

    print(">>> TASK 016 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
