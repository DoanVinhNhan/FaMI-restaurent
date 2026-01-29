from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sales.models import RestaurantTable, Order, OrderDetail
from menu.models import MenuItem, Category

User = get_user_model()

class SalesViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='password')
        self.client = Client()
        self.client.login(username='cashier', password='password')
        
        # Seed Data
        self.table = RestaurantTable.objects.create(table_name="T-01", status="AVAILABLE")
        self.category = Category.objects.create(name="Drinks")
        self.item = MenuItem.objects.create(
            sku="TEA-01", name="Ice Tea", price=20000, category=self.category, status='ACTIVE'
        )

    def test_pos_access(self):
        response = self.client.get(reverse('sales:pos_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'T-01')

    def test_add_to_cart(self):
        url = reverse('sales:pos_add_item', args=[self.table.pk, self.item.pk])
        # Using GET because verification script allowed it, or strictly POST?
        # View checks method but allows verify. Let's use POST. # No, wait, view says allow GET for verify.
        # But real usage is POST via htmx.
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200) # Returns partial
        
        # Verify Order Created
        order = Order.objects.get(table=self.table, status=Order.Status.PENDING)
        self.assertEqual(order.total_amount, 20000)
        self.assertTrue(OrderDetail.objects.filter(order=order, menu_item=self.item).exists())
        
        # Verify Table Status
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, RestaurantTable.TableStatus.OCCUPIED)

    def test_submit_order(self):
        # Setup Order
        # Use Order.Status.PENDING ('Pending') matching model definition
        order = Order.objects.create(table=self.table, user=self.user, status=Order.Status.PENDING, total_amount=20000)
        OrderDetail.objects.create(order=order, menu_item=self.item, quantity=1, unit_price=20000, total_price=20000)
        
        url = reverse('sales:pos_submit_order', args=[self.table.pk])
        response = self.client.post(url)
        
        self.assertRedirects(response, reverse('sales:pos_index'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COOKING)

    def test_submit_order_blocked_when_restaurant_closed(self):
        # Ensure RESTAURANT_STATUS = CLOSED
        from core.models import SettingGroup, SystemSetting
        group, _ = SettingGroup.objects.get_or_create(group_name='General')
        SystemSetting.objects.update_or_create(
            setting_key='RESTAURANT_STATUS',
            defaults={'setting_value': 'CLOSED', 'data_type': SystemSetting.DataType.STRING, 'group': group, 'is_active': True}
        )

        # Setup pending order
        order = Order.objects.create(table=self.table, user=self.user, status=Order.Status.PENDING, total_amount=20000)
        OrderDetail.objects.create(order=order, menu_item=self.item, quantity=1, unit_price=20000, total_price=20000)

        url = reverse('sales:pos_submit_order', args=[self.table.pk])
        response = self.client.post(url)

        # Expect redirect back to table detail and order remains pending
        self.assertRedirects(response, reverse('sales:pos_table_detail', args=[self.table.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_process_payment(self):
        """
        Verify that payment processing flow works using the newly added view.
        """
        # Create an order in COOKING status
        order = Order.objects.create(table=self.table, user=self.user, status=Order.Status.COOKING, total_amount=25000)
        OrderDetail.objects.create(order=order, menu_item=self.item, quantity=1, unit_price=25000, total_price=25000)
        
        url = reverse('sales:process_payment', args=[self.table.pk])
        
        # GET shows form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '25000')
        
        # POST performs payment
        response = self.client.post(url, {
            'payment_method': 'CASH',
            'received_amount': 30000
        })
        
        # Redirects to index
        self.assertRedirects(response, reverse('sales:pos_index'))
        
        # Verify DB Updates
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, RestaurantTable.TableStatus.DIRTY)
        
        from sales.models import Invoice, Transaction
        self.assertTrue(Invoice.objects.filter(order=order).exists())
        self.assertTrue(Transaction.objects.filter(order=order).exists())
