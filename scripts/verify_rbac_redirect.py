import sys
import os
import django
from django.test import Client
from django.urls import reverse

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def test_rbac_redirect():
    # Create Cashier
    username = 'test_cashier_rbac'
    password = 'password123'
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username=username, password=password, role='CASHIER')
    
    client = Client()
    client.login(username=username, password=password)
    
    # Try accessing Dashboard (Restricted to Manager)
    url = reverse('core:dashboard')
    print(f"Testing access to {url} as Cashier...")
    
    response = client.get(url)
    
    if response.status_code == 302:
        print("✅ Success: Redirected (302)")
        print(f"   Target: {response.url}")
        if reverse('sales:pos_index') in response.url:
             print("   -> Correctly redirected to POS Index")
        else:
             print(f"   -> WARNING: Redirected to unexpected URL: {response.url}")
    elif response.status_code == 403:
        print("❌ Failed: Validated 403 Forbidden (Should be Redirect)")
    elif response.status_code == 200:
        print("❌ Failed: Access Granted (200) - Security Breach!")
    else:
        print(f"❌ Failed: Status {response.status_code}")

if __name__ == "__main__":
    test_rbac_redirect()
