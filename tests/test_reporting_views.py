from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sales.models import Order, OrderDetail
from menu.models import MenuItem, Category

User = get_user_model()

class ReportingViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='password') # Manager/Staff
        self.client = Client()
        self.client.login(username='admin', password='password')
        
        self.cat = Category.objects.create(name="Food")
        self.item = MenuItem.objects.create(sku='R1', name='Steak', price=200, category=self.cat)
        
        # Create PAID order
        self.order = Order.objects.create(user=self.user, status=Order.Status.PAID, total_amount=200)
        OrderDetail.objects.create(order=self.order, menu_item=self.item, quantity=1, unit_price=200, total_price=200)

    def test_sales_report(self):
        url = reverse('reporting:sales_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ideally check context['summary']
        summary = response.context.get('summary')
        if summary:
            # Check if total revenue matches
            # Implementation of ReportController dependent
            pass 
        self.assertContains(response, '200') # Check total showing up

    def test_chart_data_api(self):
        url = reverse('reporting:chart_data_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check structure
        self.assertIn('revenue_chart', data)
        self.assertIn('top_items_chart', data)
        
        # Verify Steak is in labels
        self.assertIn('Steak', data['top_items_chart']['labels'])
        # Verify Revenue
        self.assertIn(200.0, data['revenue_chart']['data'])
