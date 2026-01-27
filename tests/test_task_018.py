import os
import sys
import django
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.views import add_to_cart, pos_index, remove_from_cart
from sales.models import RestaurantTable, Order, OrderDetail
from menu.models import MenuItem, Category, Pricing

def run_test():
    print(">>> STARTING TASK 018 VERIFICATION (POS View)")
    User = get_user_model()
    factory = RequestFactory()

    # Setup Data
    user, _ = User.objects.get_or_create(username='cashier_test')
    cat, _ = Category.objects.get_or_create(name='Drinks')
    table, _ = RestaurantTable.objects.get_or_create(table_name='T-POS', capacity=4, defaults={'status': 'AVAILABLE'})
    item, _ = MenuItem.objects.get_or_create(sku='POS-COKE', defaults={'name': 'Coke', 'price': 2.50, 'category': cat, 'status': 'ACTIVE'})
    Pricing.objects.create(menu_item=item, selling_price=Decimal('2.50'), effective_date=timezone.now())

    # 1. Test POS Index
    print("\nTest 1: POS Index View...")
    request = factory.get(reverse('sales:pos_index'))
    request.user = user
    response = pos_index(request)
    if response.status_code == 200:
        print("PASS: POS Index Accessed (200 OK)")
    else:
        print(f"FAIL: POS Index Status {response.status_code}")

    # 2. Test Add Item (Simulate HTMX)
    print("\nTest 2: Add Item to Cart (HTMX)...")
    url = reverse('sales:pos_add_item', args=[table.table_id, item.id])
    request = factory.post(url)
    request.user = user
    request.META['HTTP_HX_REQUEST'] = 'true' # Simulate HTMX

    # Clear old orders
    Order.objects.filter(table=table).delete()

    response = add_to_cart(request, table.table_id, item.id)
    
    # Check Response
    if response.status_code == 200:
        print("PASS: Add Item Response 200 OK")
    else:
        print(f"FAIL: Add Item Status {response.status_code}")

    # Check DB
    order = Order.objects.get(table=table, status='Pending')
    if order.total_amount == Decimal('2.50'):
        print(f"PASS: Order Created with Total {order.total_amount}")
    else:
        print(f"FAIL: Order Total is {order.total_amount}")
    
    # 3. Test Add Same Item (Increment)
    print("\nTest 3: Increment Quantity...")
    add_to_cart(request, table.table_id, item.id) # Call again
    order.refresh_from_db()
    detail = order.details.first()
    if detail.quantity == 2 and order.total_amount == Decimal('5.00'):
        print(f"PASS: Quantity incremented to {detail.quantity}, Total {order.total_amount}")
    else:
        print(f"FAIL: Qty {detail.quantity}, Total {order.total_amount}")

    # 4. Test Remove Item
    print("\nTest 4: Remove Item...")
    detail_id = detail.id
    url_rem = reverse('sales:pos_remove_item', args=[table.table_id, detail_id])
    req_rem = factory.post(url_rem)
    req_rem.user = user
    
    remove_from_cart(req_rem, table.table_id, detail_id)
    
    order.refresh_from_db()
    detail.refresh_from_db()
    if detail.quantity == 1 and order.total_amount == Decimal('2.50'):
         print(f"PASS: Decremented correctly. Qty {detail.quantity}, Total {order.total_amount}")
    else:
         print(f"FAIL: Remove logic failed. Qty {detail.quantity}")

    print(">>> TASK 018 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
