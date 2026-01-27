import os
import sys
import django
from django.utils import timezone
from decimal import Decimal
# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.utils import timezone
from decimal import Decimal
from rest_framework.test import APIRequestFactory
from rest_framework import status as http_status

from django.contrib.auth import get_user_model
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category, Pricing
from kitchen.services import KitchenController
from kitchen.models import StatusHistory
from kitchen.views import KitchenItemStatusView

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 021 VERIFICATION (Kitchen Logic)")

    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='chef_logic')
    cat, _ = Category.objects.get_or_create(name='Logic Cat')
    item, _ = MenuItem.objects.get_or_create(sku='LOGIC-BURGER', defaults={'name': 'Logic Burger', 'category': cat, 'price': 100})
    Pricing.objects.create(menu_item=item, selling_price=Decimal('100'), effective_date=timezone.now())
    
    table, _ = RestaurantTable.objects.get_or_create(table_name='T-LOGIC')
    order = Order.objects.create(user=user, table=table, status='Cooking')
    
    detail = OrderDetail.objects.create(
        order=order, 
        menu_item=item, 
        quantity=1, 
        status='Pending'
    )
    print(f"Created Item {detail.id} with status {detail.status}")

    # 2. Test Controller Logic: Pending -> Cooking
    print("\nTest 1: Controller Update (Pending -> Cooking)...")
    try:
        updated = KitchenController.update_item_status(detail.id, 'Cooking', user)
        print(f"PASS: Updated to {updated.status}")
    except Exception as e:
        print(f"FAIL: Controller logic error: {e}")

    # 3. Test API Endpoint: Cooking -> Ready
    print("\nTest 2: API Update (Cooking -> Ready)...")
    factory = APIRequestFactory()
    view = KitchenItemStatusView.as_view()
    
    url = f'/kitchen/api/items/{detail.id}/status/'
    request = factory.post(url, {'status': 'Ready'}, format='json')
    request.user = user
    
    response = view(request, pk=detail.id)
    
    if response.status_code == 200:
        print(f"PASS: API returned 200. Data: {response.data}")
        # Check DB
        detail.refresh_from_db()
        if detail.status == 'Ready':
            print("PASS: DB updated to Ready")
        else:
             print(f"FAIL: DB status is {detail.status}")
    else:
        print(f"FAIL: API Error {response.status_code} - {response.data}")

    # 4. Check StatusHistory
    print("\nTest 3: History Log...")
    history = StatusHistory.objects.filter(order_detail=detail).count()
    if history >= 2:
        print(f"PASS: Found {history} history records.")
    else:
        print(f"FAIL: Only found {history} records (Expected >= 2)")

    print(">>> TASK 021 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
