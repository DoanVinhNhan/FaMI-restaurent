from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from decimal import Decimal
from sales.models import RestaurantTable, Order, OrderDetail, Transaction, Promotion, DiscountType
from menu.models import MenuItem, Category
from sales.views import process_payment
from sales.services import PaymentController

User = get_user_model()

class PaymentProcessingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='cashier', password='password')
        
        # Setup Data
        self.table = RestaurantTable.objects.create(table_name="Table 1", status="OCCUPIED")
        self.category = Category.objects.create(name="Food")
        self.item = MenuItem.objects.create(name="Steak", price=Decimal('500.00'), category=self.category)
        
        self.order = Order.objects.create(table=self.table, user=self.user, status=Order.Status.COOKING, total_amount=Decimal('500.00'))
        OrderDetail.objects.create(order=self.order, menu_item=self.item, quantity=1, unit_price=Decimal('500.00'), total_price=Decimal('500.00'))
        self.order.update_total() # Ensure total is set

    def test_cash_payment_success_with_change(self):
        # Pay 600 for 500 bill -> Change 100
        request = self.factory.post('/sales/pos/table/1/pay/', {
            'payment_method': 'CASH',
            'received_amount': '600.00'
        })
        request.user = self.user
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        response = process_payment(request, self.table.pk)
        
        self.assertEqual(response.status_code, 302) # Redirects on success
        
        self.order.refresh_from_db()
        self.table.refresh_from_db() # Refresh table status
        
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.table.status, RestaurantTable.TableStatus.AVAILABLE) # Should free table
        
        tx = Transaction.objects.last()
        self.assertEqual(tx.amount, Decimal('600.00'))
        self.assertEqual(tx.status, Transaction.PaymentStatus.SUCCESS)

    def test_promotion_application(self):
        # Create Promo: 10% off
        Promotion.objects.create(
            name="Test Promo",
            promo_code="SAVE10", 
            discount_type=DiscountType.PERCENTAGE, 
            discount_value=10, 
            start_date="2020-01-01 00:00", 
            end_date="2099-01-01 00:00"
        )
        
        # Pay exactly discounted amount (450)
        start_total = self.order.total_amount # 500
        
        result = PaymentController.process_payment(
            self.order.id, 
            amount=Decimal('450.00'), 
            method='CASH', 
            promo_code='SAVE10'
        )
        
        self.assertTrue(result['success'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_amount, Decimal('450.00')) # Total updated
        self.assertEqual(self.order.status, Order.Status.PAID)

    def test_insufficient_payment(self):
        request = self.factory.post('/sales/pos/table/1/pay/', {
            'payment_method': 'CASH',
            'received_amount': '400.00' # Bill is 500
        })
        request.user = self.user
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        response = process_payment(request, self.table.pk)
        
        # Should stay on page (200 OK) or handle error message. 
        # In current view implementation, it falls through to render same page.
        self.assertEqual(response.status_code, 200) 
        
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.PAID)
