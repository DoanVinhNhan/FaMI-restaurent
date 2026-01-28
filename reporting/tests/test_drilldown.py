from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from sales.models import Order, OrderDetail, MenuItem

class SalesDrilldownViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = self._create_user()
        self.client.force_login(self.user)
        # Create an item and an order
        self.item = MenuItem.objects.create(name='TestDish', price=10000)
        self.order = Order.objects.create(user=self.user, total_amount=10000, status=Order.Status.PAID)
        OrderDetail.objects.create(order=self.order, menu_item=self.item, quantity=1, unit_price=10000, total_price=10000)

    def _create_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create(username='reporter', password='pass', role='MANAGER', is_superuser=False)

    def test_sales_drilldown_returns_orders(self):
        start = (timezone.now() - timedelta(days=7)).date().isoformat()
        end = timezone.now().date().isoformat()
        url = reverse('reporting:sales_drilldown') + f'?item={self.item.name}&start_date={start}&end_date={end}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestDish')
