import os
import sys
import django
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from menu.models import MenuItem, Pricing, Category
from django.urls import reverse

class MenuViewsTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username='manager_test_012', password='password')
        self.cat, _ = Category.objects.get_or_create(name="Food Test")
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_create_menu_item(self):
        print("Test 1: Creating Menu Item + Pricing Transaction...")
        
        data = {
            'sku': 'TEST-VIEW-001',
            'name': 'Test Burger View',
            'category': self.cat.id,
            'description': 'Delicious',
            'status': 'ACTIVE',
            'selling_price': '55000',
            'effective_date': '2025-01-01'
        }
        
        # Use Client to POST
        response = self.client.post(reverse('menu:menu_create'), data)
        
        if response.status_code == 302:
            print("PASS: View returned redirect (302)")
            item = MenuItem.objects.get(sku='TEST-VIEW-001')
            print(f"PASS: MenuItem created: {item.name}")
            pricing = Pricing.objects.get(menu_item=item)
            if pricing.selling_price == Decimal('55000'):
                print(f"PASS: Initial Pricing created: {pricing.selling_price}")
            else:
                print(f"FAIL: Pricing mismatch. Got {pricing.selling_price}")
        else:
             print(f"FAIL: Expected 302, got {response.status_code}")
             if response.context:
                 if 'item_form' in response.context:
                     print(f"Item Form Errors: {response.context['item_form'].errors}")
                 if 'price_form' in response.context:
                     print(f"Price Form Errors: {response.context['price_form'].errors}")
             
             # Print Messages
             try:
                 from django.contrib.messages import get_messages
                 msgs = list(get_messages(response.wsgi_request))
                 print(f"Messages: {[str(m) for m in msgs]}")
                 # Also check context messages
                 if 'messages' in response.context:
                      print(f"Context Messages: {[str(m) for m in response.context['messages']]}")
             except Exception:
                 pass

    def test_soft_delete(self):
        print("\nTest 2: Soft Delete...")
        # Create item
        item = MenuItem.objects.create(
            sku='DEL-001', 
            name='To Delete', 
            category=self.cat, 
            price=100,
            status='ACTIVE'
        )
        
        response = self.client.post(reverse('menu:menu_delete', args=[item.pk]))
        if response.status_code == 302:
            item.refresh_from_db()
            if item.status == 'INACTIVE': # Check string value or choice
                print("PASS: Item status set to INACTIVE")
            else:
                print(f"FAIL: Item status is {item.status}")
        else:
            print(f"FAIL: Expected 302, got {response.status_code}")

if __name__ == '__main__':
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=1)
    failures = runner.run_tests(['tests.test_task_012'])
    if failures:
        sys.exit(failures)
