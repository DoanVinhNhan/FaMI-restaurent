
import os
import django
import json
from rest_framework.test import APIClient
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from menu.models import MenuItem, Category
from sales.models import RestaurantTable, Order

User = get_user_model()

def run_verification():
    print(">>> STARTING VERIFICATION: API Sync Endpoints")

    # 1. Setup Test Data
    try:
        # Create a user (Cashier)
        user, created = User.objects.get_or_create(
            username='sync_test_user',
            defaults={'role': 'Cashier', 'email': 'sync@fami.com'}
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        # Create a Table
        table, _ = RestaurantTable.objects.get_or_create(table_name="OFF-01", capacity=4)
        
        # Create Menu Item
        cat, _ = Category.objects.get_or_create(name="Test Category")
        item, _ = MenuItem.objects.get_or_create(
            name="Offline Burger",
            defaults={'sku': 'OFF-BG-001', 'price': 50000, 'category': cat}
        )

        print(f"[OK] Setup Data: User ID {user.id}, Table ID {table.table_id}, Item ID {item.id}")

    except Exception as e:
        print(f"[FAIL] Setup Data: {e}")
        return

    # 2. Prepare Payload (Bulk Orders)
    payload = [
        {
            "table": table.table_id,
            "user": user.id,
            "total_amount": 100000.00,
            "status": "Paid",
            "created_at": datetime.now().isoformat(),
            "items": [
                {
                    "item_id": item.id,
                    "quantity": 2,
                    "price_snapshot": 50000.00,
                    "note": "No onions"
                }
            ]
        },
        {
            "table": table.table_id,
            "user": user.id,
            "total_amount": 50000.00,
            "status": "Pending",
            "created_at": datetime.now().isoformat(),
            "items": [
                {
                    "item_id": item.id,
                    "quantity": 1,
                    "price_snapshot": 50000.00,
                    "note": ""
                }
            ]
        }
    ]

    # 3. Perform Request
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = '/sales/api/sync/orders/'
    print(f">>> Sending POST request to {url} with {len(payload)} orders...")
    
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json'
    )

    # 4. Verify Response
    if response.status_code == 201:
        print(f"[OK] Response Status: {response.status_code}")
        print(f"[INFO] Response Body: {response.json()}")
        
        # Verify DB
        synced_ids = response.json().get('order_ids', [])
        db_count = Order.objects.filter(id__in=synced_ids).count()
        if db_count == len(payload):
            print(f"[SUCCESS] {db_count} orders verified in Database.")
        else:
            print(f"[FAIL] Expected {len(payload)} orders in DB, found {db_count}.")
    else:
        print(f"[FAIL] Response Status: {response.status_code}")
        print(f"[FAIL] Errors: {response.json()}")

if __name__ == "__main__":
    run_verification()
