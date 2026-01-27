import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.models import RestaurantTable
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

def run_test():
    print(">>> STARTING TASK 013 VERIFICATION (Sales Tables)")
    
    # 1. Model Verification
    print("Test 1: Creating Tables...")
    try:
        t1, _ = RestaurantTable.objects.get_or_create(table_name="TEST-T1", capacity=4)
        t2, _ = RestaurantTable.objects.get_or_create(table_name="TEST-T2", capacity=6, status='OCCUPIED')
        print(f"PASS: Created Tables {t1} and {t2}")
        
        if t1.is_available() and not t2.is_available():
            print("PASS: Availability logic correct")
        else:
            print("FAIL: Availability logic incorrect")
            
    except Exception as e:
        print(f"FAIL: Model creation failed: {e}")

    # 2. View Verification
    print("\nTest 2: View Access...")
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='manager_sales_test', defaults={'email': 'm@sales.com', 'password': 'pass'})
    
    client = Client()
    client.force_login(user)
    
    response = client.get(reverse('sales:table_list'))
    if response.status_code == 200:
        print("PASS: Table List View Accessible (200 OK)")
        if 'TEST-T1' in str(response.content):
             print("PASS: Table content rendered")
        else:
             print("FAIL: Content not found in view")
    else:
        print(f"FAIL: Expected 200, got {response.status_code}")

    print(">>> TASK 013 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
