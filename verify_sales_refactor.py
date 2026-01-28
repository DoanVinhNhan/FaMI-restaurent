import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.test import Client, RequestFactory
from django.urls import reverse
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category
from django.contrib.auth import get_user_model
from sales.services import PaymentController

User = get_user_model()

def verify_sales_refactor():
    print("=== STARTING SALES MODULE VERIFICATION ===")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='tester', defaults={'is_superuser': True})
    cat, _ = Category.objects.get_or_create(name="TestCat")
    item, _ = MenuItem.objects.get_or_create(name="TestItem", defaults={'price': 10000, 'category': cat, 'status': 'ACTIVE', 'sku': 'TEST001'})
    
    # 2. Test 3rd Party API (Create Order)
    print("\n[1] Testing Create 3rd Party Order API...")
    client = Client()
    payload = {
        "partner_order_id": "GRAB-999",
        "items": [
            {"sku": "TEST001", "quantity": 2} # Total 20,000
        ]
    }
    
    response = client.post(reverse('sales:api_create_order'), payload, content_type='application/json')
    print(f"API Response: {response.status_code} - {response.json()}")
    
    if response.status_code == 201:
        order_id = response.json()['order_id']
        order = Order.objects.get(pk=order_id)
        if order.total_amount == 20000 and order.status == Order.Status.COOKING:
             print("SUCCESS: 3rd Party Order created correctly.")
        else:
             print(f"FAIL: Order data mismatch. Total: {order.total_amount}, Status: {order.status}")
    else:
        print("FAIL: API Request failed.")

    # 3. Test Payment Controller Direct Call
    print("\n[2] Testing PaymentController Logic...")
    # Create a local order
    table, _ = RestaurantTable.objects.get_or_create(table_name="PAY-TEST")
    local_order = Order.objects.create(table=table, total_amount=50000, status=Order.Status.COOKING, user=user)
    
    result = PaymentController.process_payment(
        order_id=local_order.id,
        amount=Decimal(50000),
        method="CASH"
    )
    
    if result['success']:
        local_order.refresh_from_db()
        if local_order.status == Order.Status.PAID:
             print(f"SUCCESS: Payment processed. Invoice ID: {result['invoice_id']}")
        else:
             print("FAIL: Order status not updated to PAID.")
    else:
        print(f"FAIL: Payment Controller returned error: {result['message']}")

    # 4. Test View Integration (Simulate Post)
    print("\n[3] Testing Payment View Integration...")
    # Create another order
    view_order = Order.objects.create(table=table, total_amount=10000, status=Order.Status.COOKING, user=user)
    
    factory = RequestFactory()
    url = reverse('sales:process_payment', args=[table.pk])
    request = factory.post(url, {'payment_method': 'CARD', 'received_amount': 10000})
    request.user = user
    request._messages = [] # Mock messages
    
    # We need to import the view function directly or use Client
    # Using Client is better for full integration
    client.force_login(user)
    resp = client.post(url, {'payment_method': 'CARD', 'received_amount': 10000})
    
    view_order.refresh_from_db()
    if view_order.status == Order.Status.PAID:
        print("SUCCESS: View successfully utilized PaymentController.")
    else:
         print(f"FAIL: View failed to process payment. Status: {view_order.status}")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify_sales_refactor()
