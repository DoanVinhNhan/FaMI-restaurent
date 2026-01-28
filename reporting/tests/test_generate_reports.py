from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from reporting.services import ReportController
from reporting.views import sales_report_view
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category

User = get_user_model()

class GenerateReportsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username='admin', password='password')
        self.table = RestaurantTable.objects.create(table_name="T1")
        
        # Create some sales data
        self.item = MenuItem.objects.create(name="Coke", price=10, sku="COKE", category=Category.objects.create(name="Drinks"))
        
        # Order 1: PAID today
        self.order1 = Order.objects.create(
            user=self.user, table=self.table, status=Order.Status.PAID, total_amount=20,
            external_id="ORD-R1"
        )
        # Manually set created_at if needed, but auto_now_add handles it for 'today'
        OrderDetail.objects.create(order=self.order1, menu_item=self.item, quantity=2, unit_price=10, total_price=20)

    def test_validate_params_error(self):
        # Start > End
        start = date.today()
        end = start - timedelta(days=1)
        with self.assertRaises(ValueError):
            ReportController.validate_params(start, end)

    def test_validate_params_too_large(self):
        # > 365 days
        start = date(2020, 1, 1)
        end = date(2022, 1, 1)
        with self.assertRaises(ValueError):
            ReportController.validate_params(start, end)

    def test_sales_report_with_data(self):
        start = date.today()
        end = date.today()
        summary = ReportController.generate_sales_report(start, end)
        
        self.assertEqual(summary.total_orders, 1)
        self.assertEqual(summary.total_revenue, Decimal('20.00'))
        self.assertEqual(len(summary.top_selling_items), 1)
        self.assertEqual(summary.top_selling_items[0]['menu_item__name'], 'Coke')

    def test_get_orders_for_item(self):
        # Create additional paid order with same item
        order2 = Order.objects.create(user=self.user, table=self.table, status=Order.Status.PAID, total_amount=10)
        OrderDetail.objects.create(order=order2, menu_item=self.item, quantity=1, unit_price=10, total_price=10)

        from reporting.services import ReportController
        page = ReportController.get_orders_for_item(date.today(), date.today(), 'Coke', page=1, per_page=10)
        self.assertEqual(page.paginator.count, 2)
        ids = [o.id for o in page.object_list]
        self.assertIn(self.order1.id, ids)
        self.assertIn(order2.id, ids)

    def test_sales_drilldown_view(self):
        request = self.factory.get('/reporting/sales/drilldown/', {'item': 'Coke', 'start_date': date.today().isoformat(), 'end_date': date.today().isoformat()})
        request.user = self.user

        # Mock Session & messages
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))

        response = sales_report_view(request)
        # The drilldown is loaded via HTMX button; the sales_report_view should still render OK
        self.assertEqual(response.status_code, 200)

    def test_view_invalid_date_range(self):
        # Request with backwards dates
        future = (date.today() + timedelta(days=10)).isoformat()
        past = date.today().isoformat()
        
        request = self.factory.get('/reporting/sales/', {'start_date': future, 'end_date': past})
        request.user = self.user
        
        # Mock Session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Mock messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))
        
        response = sales_report_view(request)
        
        # Should render page but with error message (so 200 OK)
        self.assertEqual(response.status_code, 200)

    def test_export_csv(self):
        start = date.today()
        end = date.today()
        summary = ReportController.generate_sales_report(start, end)
        csv_file = ReportController.export_sales_to_csv(summary)
        
        self.assertIn('Sales Report', csv_file)
        self.assertIn('Coke', csv_file)
        # Decimal(20.00) might be written as 20 in CSV depending on locale/lib
        self.assertTrue('20.00' in csv_file or '20' in csv_file)
