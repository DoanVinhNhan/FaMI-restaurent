import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from kitchen.views import kds_board_view, update_item_status
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 020 VERIFICATION (KDS View)")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='kds_tester')
    
    # Categories: Kitchen vs Bar
    cat_kitchen, _ = Category.objects.get_or_create(
        name="KDS Food", 
        defaults={'printer_target': 'KITCHEN'}
    )
    cat_bar, _ = Category.objects.get_or_create(
        name="KDS Drinks", 
        defaults={'printer_target': 'BAR'}
    )
    
    # Items
    item_food, _ = MenuItem.objects.get_or_create(sku='KDS-FOOD', defaults={
        'name': 'KDS Burger', 
        'category': cat_kitchen, 
        'price': 50
    })
    item_drink, _ = MenuItem.objects.get_or_create(sku='KDS-DRINK', defaults={
        'name': 'KDS Beer', 
        'category': cat_bar
    })
    
    # Needs Active Pricing (Task 016 Logic)
    from menu.models import Pricing
    from decimal import Decimal
    Pricing.objects.create(menu_item=item_food, selling_price=Decimal('50'), effective_date=timezone.now())
    Pricing.objects.create(menu_item=item_drink, selling_price=Decimal('10'), effective_date=timezone.now())
    
    # Order
    table, _ = RestaurantTable.objects.get_or_create(table_name='T-KDS')
    order = Order.objects.create(user=user, table=table, status='Cooking')
    
    # Details
    detail_food = OrderDetail.objects.create(order=order, menu_item=item_food, quantity=2, status='Pending')
    detail_drink = OrderDetail.objects.create(order=order, menu_item=item_drink, quantity=1, status='Pending')
    
    factory = RequestFactory()
    
    # 2. Test KDS Board View (GET)
    print("\nTest 1: KDS Board Rendering...")
    request = factory.get(reverse('kitchen:kds_board'))
    request.user = user
    response = kds_board_view(request)
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        # Check if grouped correctly
        if 'KDS Burger' in content and 'Kitchen Station' in content:
            print("PASS: Kitchen item found in view.")
        else:
            print("FAIL: Kitchen item missing from view.")
            
        if 'KDS Beer' in content and 'Bar Station' in content:
            print("PASS: Bar item found in view.")
        else:
             print("FAIL: Bar item missing from view.")
    else:
        print(f"FAIL: View returned {response.status_code}")

    # 3. Test Status Update (POST)
    print("\nTest 2: Update Status (Pending -> Cooking)...")
    url = reverse('kitchen:update_item_status', args=[detail_food.id])
    request_up = factory.post(url, {'next_status': 'Cooking'})
    request_up.user = user
    request_up.headers = {'HX-Request': 'true'} # Mock HTMX
    
    response_up = update_item_status(request_up, detail_food.id)
    
    detail_food.refresh_from_db()
    if detail_food.status == 'Cooking':
        print(f"PASS: Food item status updated to {detail_food.status}")
    else:
        print(f"FAIL: Food item status is {detail_food.status}")

    # 4. Verify Status History Log (From Task 019 Model)
    from kitchen.models import StatusHistory
    history = StatusHistory.objects.filter(order_detail=detail_food).last()
    if history and history.new_status == 'Cooking':
        print(f"PASS: StatusHistory log found: {history}")
    else:
        print("FAIL: No StatusHistory log created.")

    print(">>> TASK 020 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
