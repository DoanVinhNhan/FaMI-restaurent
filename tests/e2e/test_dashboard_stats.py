
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category
from core.models import User
from decimal import Decimal
from django.utils import timezone
import datetime
import json

class TestDashboardStats(TestCase):
    def setUp(self):
        # 1. Setup User (Manager)
        self.user = User.objects.create_superuser('manager', 'manager@fami.local', 'password')
        self.client = Client()
        self.client.force_login(self.user)

        # 2. Setup Data
        self.category = Category.objects.create(name="Food", printer_target="KITCHEN")
        self.item = MenuItem.objects.create(name="Pho Bo", price=50000, category=self.category, status='ACTIVE')
        self.table = RestaurantTable.objects.create(table_name="T1", status=RestaurantTable.TableStatus.OCCUPIED)

        # 3. Create Orders for Today
        # Order 1: Paid (Should count for revenue)
        order1 = Order.objects.create(user=self.user, table=self.table, status=Order.Status.PAID, total_amount=100000)
        OrderDetail.objects.create(order=order1, menu_item=self.item, quantity=2, unit_price=50000, total_price=100000, status=Order.Status.PAID)
        # Manually set created_at to today (auto_now_add usually handles this, but ensuring)
        
        # Order 2: Pending (Should count for order count, but maybe not revenue depending on logic?)
        # Core views logic: revenue is filter(status=PAID). Orders today is ALL orders.
        order2 = Order.objects.create(user=self.user, table=self.table, status=Order.Status.PENDING)
        
    def test_core_dashboard_stats(self):
        """
        Verify that the main dashboard displays correct summary statistics.
        """
        url = reverse('core:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Context checks
        context = response.context
        self.assertEqual(context['orders_today'], 2, "Should have 2 orders today")
        self.assertEqual(context['revenue_today'], 100000, "Revenue should be 100,000")
        
        # HTML checks
        content = response.content.decode()
        self.assertIn("100,000", content) # formatted with intcomma usually
        # The dashboard activity table shows Order ID, not Items. 
        self.assertIn("#1", content)
        self.assertIn("#2", content)

    def test_chart_data_api(self):
        """
        Verify that the Chart Data API returns correct JSON structure and data.
        """
        # Correct URL name from reporting/urls.py
        url = reverse('reporting:chart_data_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Structure Check
        self.assertIn('revenue_chart', data)
        self.assertIn('top_items_chart', data)
        
        # Data Check
        revenue_chart = data['revenue_chart']
        self.assertTrue(len(revenue_chart['labels']) > 0)
        self.assertTrue(len(revenue_chart['data']) > 0)
        # We expect at least today's data provided we have revenue
        # Note: Chart query groups by day.
        
        top_items = data['top_items_chart']
        self.assertIn("Pho Bo", top_items['labels'])
        # quantity was 2
        idx = top_items['labels'].index("Pho Bo")
        self.assertEqual(top_items['data'][idx], 2)

