
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem, Category
from core.models import User

class TestKitchenFlow(TestCase):
    def setUp(self):
        # 1. Setup User (Chef/Admin)
        self.user = User.objects.create_superuser('chef', 'chef@fami.local', 'password')
        self.client = Client()
        self.client.force_login(self.user)

        # 2. Setup Data
        self.category = Category.objects.create(name="Food", printer_target="KITCHEN")
        self.item = MenuItem.objects.create(name="Pho Bo", price=50000, category=self.category, status='ACTIVE')
        self.table = RestaurantTable.objects.create(table_name="T1", status=RestaurantTable.TableStatus.OCCUPIED)

    def test_full_kitchen_lifecycle(self):
        """
        Verifies the complete lifecycle of an item on the Kitchen Display System (KDS).
        1. Order Created (Sales)
        2. Appears on KDS (Pending)
        3. Cook clicks 'Cook' -> Status: Cooking
        4. Cook clicks 'Done' -> Status: Paid/Ready -> Disappears from Board
        """
        
        # 1. Create Order (Simulation of Sales App)
        order = Order.objects.create(user=self.user, table=self.table, status=Order.Status.PENDING)
        detail = OrderDetail.objects.create(
            order=order, 
            menu_item=self.item, 
            quantity=2, 
            unit_price=self.item.price,
            total_price=self.item.price * 2,
            status=Order.Status.PENDING
        )
        
        print(f"\n[Step 1] Order #{order.id} Created with Item {detail.id} (Status: {detail.status})")

        # 2. Verify Appearance on KDS
        url = reverse('kitchen:kds_board')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        
        # Check if item name and quantity are present
        self.assertIn("Pho Bo", content, "Item name not found on KDS board")
        self.assertIn("2x", content, "Item quantity 2x not found on KDS board")
        self.assertIn("Cook", content, "'Cook' button should be visible for Pending items")

        print("[Step 2] Item verified on KDS Board")

        # 3. Transition: Pending -> Cooking
        # Simulate HTMX Post
        update_url = reverse('kitchen:update_item_status', args=[detail.id])
        response = self.client.post(update_url, {'next_status': Order.Status.COOKING}, headers={'HX-Request': 'true'})
        
        self.assertEqual(response.status_code, 200)
        
        detail.refresh_from_db()
        self.assertEqual(detail.status, Order.Status.COOKING, "Item status did not update to COOKING")
        
        # Check response content for updated button state
        content = response.content.decode()
        self.assertIn("Ready", content, "'Ready' button should be visible for Cooking items")
        print(f"[Step 3] Item moved to Cooking (Status: {detail.status})")

        # 4. Transition: Cooking -> Ready
        response = self.client.post(update_url, {'next_status': Order.Status.READY}, headers={'HX-Request': 'true'})
        self.assertEqual(response.status_code, 200)
        
        detail.refresh_from_db()
        self.assertEqual(detail.status, Order.Status.READY, "Item status did not update to READY")

        content = response.content.decode()
        self.assertIn("Serve", content, "'Serve' button should be visible for Ready items")
        print(f"[Step 4] Item moved to Ready (Status: {detail.status})")

        # 5. Transition: Ready -> Served (Complete)
        response = self.client.post(update_url, {'next_status': Order.Status.SERVED}, headers={'HX-Request': 'true'})
        self.assertEqual(response.status_code, 200)
        
        detail.refresh_from_db()
        self.assertEqual(detail.status, Order.Status.SERVED, "Item status did not update to SERVED")
        
        # Verify it's GONE from the active board view
        content = response.content.decode()
        
        if "Pho Bo" not in content:
             print("[Step 5] Item successfully removed from KDS Board after completion.")
        else:
             self.fail("Item 'Pho Bo' still visible on KDS after being marked Served!")
