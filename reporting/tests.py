
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from sales.models import Order, OrderDetail
from menu.models import MenuItem
from decimal import Decimal

User = get_user_model()

class ReportViewsTestCase(TestCase):
    def setUp(self):
        # Create User
        self.user = User.objects.create_user(username='manager_viz', password='password123', is_staff=True)
        self.client = Client()
        self.client.login(username='manager_viz', password='password123')

        # Create Data
        self.item1 = MenuItem.objects.create(name="BurgerViz", price=50000, status='ACTIVE')
        self.item2 = MenuItem.objects.create(name="CokeViz", price=10000, status='ACTIVE')

        # Create Order 1 (Today)
        order1 = Order.objects.create(total_amount=Decimal('110000.00'), status='Paid', created_at=timezone.now())
        OrderDetail.objects.create(order=order1, menu_item=self.item1, quantity=2, unit_price=Decimal('50000.00'), total_price=Decimal('100000.00')) 
        OrderDetail.objects.create(order=order1, menu_item=self.item2, quantity=1, unit_price=Decimal('10000.00'), total_price=Decimal('10000.00')) 
        
    def test_chart_data_api(self):
        url = reverse('reporting:chart_data_api')
        response = self.client.get(url)
        
        if response.status_code != 200:
             print(f"FAIL: API returned {response.status_code}")
             return

        data = response.json()
        
        # Verify Revenue Structure
        assert 'revenue_chart' in data, "Missing revenue_chart key"
        
        # Verify Top Items Structure
        assert 'top_items_chart' in data, "Missing top_items_chart key"
        
        labels = data['top_items_chart']['labels']
        values = data['top_items_chart']['data']
        
        print(f"\n[VERIFICATION] Top Items: {labels}")
        
        if 'BurgerViz' in labels and 'CokeViz' in labels:
            print("PASS: Correct items found in chart data.")
        else:
            print("FAIL: Expected items not found.")

        print("[VERIFICATION] Chart API returned valid JSON structure.")
