import os
import django
from django.test import Client
from django.urls import reverse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

def test_auth_flow():
    client = Client()
    
    print("1. Testing Login Page availability...")
    try:
        url = reverse('core:login')
        response = client.get(url)
        if response.status_code == 200:
            print("   [PASS] Login page is accessible (200 OK).")
            if 'Đăng nhập Hệ thống' in response.content.decode('utf-8'):
                print("   [PASS] Login template content verified.")
            else:
                print("   [FAIL] Login template content mismatch.")
        else:
            print(f"   [FAIL] Login page returned status {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error accessing login page: {e}")

    print("\n2. Testing Dashboard Protection...")
    try:
        url = reverse('core:dashboard')
        response = client.get(url)
        # Should redirect to login because we are not logged in
        if response.status_code == 302:
            print("   [PASS] Unauthenticated access to dashboard redirects (302 Found).")
            if '/login/' in response.url:
                 print("   [PASS] Redirects specifically to login page.")
            else:
                 print(f"   [FAIL] Redirects to unexpected URL: {response.url}")
        else:
            print(f"   [FAIL] Expected 302, got {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error accessing dashboard: {e}")

if __name__ == "__main__":
    test_auth_flow()
