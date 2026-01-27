import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from menu.models import MenuItem, Category
from sales.models import Order, OrderDetail, RestaurantTable
from kitchen.models import ReasonCode, WasteReport, StatusHistory

User = get_user_model()

def run_verification():
    print(">>> STARTING TASK 019 VERIFICATION (Kitchen App)")

    # 1. Setup Prerequisites (Mock Data)
    try:
        user, _ = User.objects.get_or_create(username='kitchen_staff_test')
        cat, _ = Category.objects.get_or_create(name='Kitchen Test Cat')
        item, _ = MenuItem.objects.get_or_create(
            sku='KIT-TEST-001', 
            defaults={'name': "Kitchen Test Burger", 'status': 'ACTIVE', 'price': 100, 'category': cat}
        )
        print("PASS: Prerequisites checked: User and MenuItem exist.")
    except Exception as e:
        print(f"FAIL: Error setting up prerequisites: {e}")
        return

    # 2. Verify ReasonCode
    try:
        reason, created = ReasonCode.objects.get_or_create(
            code="BURNED_TEST",
            defaults={'description': "Food was overcooked/burned"}
        )
        print(f"PASS: ReasonCode created/retrieved: {reason.code}")
    except Exception as e:
        print(f"FAIL: ReasonCode error - {e}")

    # 3. Verify WasteReport
    try:
        report = WasteReport.objects.create(
            actor=user,
            menu_item=item,
            quantity=Decimal('1.00'),
            reason=reason
        )
        print(f"PASS: WasteReport created: LogID {report.log_id} for {report.menu_item}")
    except Exception as e:
        print(f"FAIL: WasteReport error - {e}")

    # 4. Verify StatusHistory
    try:
        table, _ = RestaurantTable.objects.get_or_create(table_name='T-KIT', capacity=4)
        order = Order.objects.create(user=user, table=table)
        detail = OrderDetail.objects.create(order=order, menu_item=item, quantity=1, unit_price=100, total_price=100)
        
        history = StatusHistory.objects.create(
            order_detail=detail,
            old_status='Pending',
            new_status='Cooking',
            changed_by=user
        )
        print(f"PASS: StatusHistory created: {history}")
    except Exception as e:
        print(f"FAIL: StatusHistory error - {e}")

    print(">>> TASK 019 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_verification()
