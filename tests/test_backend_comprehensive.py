
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from inventory.models import Ingredient, InventoryItem, StockTakeTicket, StockTakeDetail
from menu.models import Category, MenuItem, Recipe, RecipeIngredient
from sales.models import RestaurantTable, Order, OrderDetail
from sales.services import PaymentController
from kitchen.services import KitchenController
from kitchen.models import StatusHistory
from reporting.services import ReportController

User = get_user_model()

class BackendEndToEndTestCase(TestCase):
    def test_full_flow(self):
        print("\n>>> STARTING COMPREHENSIVE BACKEND TEST")

        # 1. SETUP USERS
        admin = User.objects.create_superuser('admin', 'admin@fami.com', 'admin123')
        cashier = User.objects.create_user('cashier', 'cashier@fami.com', 'cashier123', role='Cashier')
        chef = User.objects.create_user('chef', 'chef@fami.com', 'chef123', role='Kitchen')
        print("[OK] Users Created")

        # 2. INVENTORY SETUP
        # Meat: 10kg, Cost 100k/kg
        meat = Ingredient.objects.create(sku='ING-MEAT', name='Beef Patty', unit='kg', cost_per_unit=100000, alert_threshold=5)
        inv_meat = InventoryItem.objects.create(ingredient=meat, quantity_on_hand=10.0)
        # Bun: 20pcs, Cost 5k/pc
        bun = Ingredient.objects.create(sku='ING-BUN', name='Burger Bun', unit='pc', cost_per_unit=5000, alert_threshold=10)
        inv_bun = InventoryItem.objects.create(ingredient=bun, quantity_on_hand=20.0)
        print("[OK] Inventory Setup: Meat=10kg, Bun=20pcs")

        # 3. MENU SETUP
        cat_food = Category.objects.create(name='Food', printer_target='KITCHEN')
        burger = MenuItem.objects.create(sku='ITM-BGR', name='Classic Burger', price=150000, category=cat_food)
        
        # Recipe: 1 Burger = 0.2kg Meat + 1 Bun
        r_burger = Recipe.objects.create(menu_item=burger)
        RecipeIngredient.objects.create(recipe=r_burger, ingredient=meat, quantity=0.2, unit='kg')
        RecipeIngredient.objects.create(recipe=r_burger, ingredient=bun, quantity=1.0, unit='pc')
        print("[OK] Menu Setup: Burger Recipe (0.2kg Meat + 1 Bun)")

        # 4. SALES FLOW
        table1 = RestaurantTable.objects.create(table_name="Table 1", capacity=4)
        
        # Cashier creates Order
        order = Order.objects.create(table=table1, user=cashier, status=Order.Status.PENDING)
        # Add 2 Burgers
        # Price snapshot matches current price 150k
        detail1 = OrderDetail.objects.create(
            order=order, 
            menu_item=burger, 
            quantity=2, 
            unit_price=burger.price, 
            total_price=burger.price * 2,
            status=Order.Status.PENDING
        )
        order.update_total()
        self.assertEqual(order.total_amount, 300000)
        print(f"[OK] Order Created: {order} - Total: {order.total_amount}")

        # 5. KITCHEN FLOW
        # Chef sees pending item
        pending_items = KitchenController.get_pending_items()
        self.assertIn(detail1, pending_items)
        
        # Chef starts Cooking
        KitchenController.update_item_status(detail1.id, StatusHistory.OrderStatus.COOKING, chef)
        detail1.refresh_from_db()
        self.assertEqual(detail1.status, StatusHistory.OrderStatus.COOKING)
        
        # Chef marks Ready
        KitchenController.update_item_status(detail1.id, StatusHistory.OrderStatus.READY, chef)
        print("[OK] Kitchen Flow: Burger update to READY")
        
        # 6. PAYMENT & INVENTORY DEDUCTION
        # Cashier processes payment
        result = PaymentController.process_payment(order.id, amount=300000, method='CASH')
        self.assertTrue(result['success'])
        
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        
        # Verify Inventory Deduction
        # Sold 2 Burgers:
        # Meat usage: 2 * 0.2 = 0.4kg. Remaining: 10 - 0.4 = 9.6kg
        # Bun usage: 2 * 1 = 2pcs. Remaining: 20 - 2 = 18pcs
        
        inv_meat.refresh_from_db()
        inv_bun.refresh_from_db()
        
        self.assertAlmostEqual(float(inv_meat.quantity_on_hand), 9.6, places=2)
        self.assertAlmostEqual(float(inv_bun.quantity_on_hand), 18.0, places=2)
        print(f"[OK] Inventory Deducted Correctly: Meat={inv_meat.quantity_on_hand}, Bun={inv_bun.quantity_on_hand}")
        
        # 7. STOCK TAKING (End of Day)
        # Create Ticket
        ticket = StockTakeTicket.objects.create(code=f'ST-{timezone.now().strftime("%Y%m%d")}', creator=admin)
        
        # System calculated snapshot should be 9.6 for meat
        # Let's verify variance calculation if we count 9.5 (0.1 lost)
        detail_st = StockTakeDetail.objects.create(
            ticket=ticket,
            ingredient=meat,
            snapshot_quantity=inv_meat.quantity_on_hand, # 9.6
            actual_quantity=9.5
        )
        self.assertAlmostEqual(float(detail_st.variance), -0.1, places=2)
        print(f"[OK] Stock Take: Recorded 9.5kg Meat (Variance: {detail_st.variance})")
        
        # 8. REPORTING
        # Generate Sales Report
        today = timezone.now().date()
        summary = ReportController.generate_sales_report(today, today)
        self.assertEqual(summary['total_revenue'], 300000)
        self.assertEqual(summary['total_orders'], 1)
        print(f"[OK] Sales Report: Revenue {summary['total_revenue']}")

        print(">>> COMPREHENSIVE TEST COMPLETED SUCCESSFULLY")
