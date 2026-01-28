from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category
from decimal import Decimal

User = get_user_model()

class ChartDataAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='password')
        self.table = RestaurantTable.objects.create(table_name="T1")
        self.cat = Category.objects.create(name="Drinks")
        self.item = MenuItem.objects.create(name="Coke", price=Decimal('10.00'), sku='COKE', category=self.cat)

        # Create PAID orders
        o1 = Order.objects.create(user=self.user, table=self.table, status=Order.Status.PAID, total_amount=Decimal('20.00'))
        OrderDetail.objects.create(order=o1, menu_item=self.item, quantity=2, unit_price=Decimal('10.00'), total_price=Decimal('20.00'))

    def test_chart_data_api(self):
        self.client.force_login(self.user)
        url = reverse('reporting:chart_data_api')
        resp = self.client.get(url + '?days=30')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('revenue_chart', data)
        self.assertIn('top_items_chart', data)
        self.assertIsInstance(data['revenue_chart']['labels'], list)
        self.assertIsInstance(data['top_items_chart']['labels'], list)
