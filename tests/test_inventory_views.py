from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from inventory.models import Ingredient, InventoryItem, InventoryLog, StockTakeTicket, StockTakeDetail

User = get_user_model()

class InventoryViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='password')
        self.client = Client()
        self.client.login(username='manager', password='password')
        
        # Seed Data
        self.ingredient = Ingredient.objects.create(
            sku="ING-001", name="Rice", unit="kg", cost_per_unit=20.0
        )
        # Create InventoryItem manually since signal might not exist
        self.inv_item, created = InventoryItem.objects.get_or_create(
            ingredient=self.ingredient, 
            defaults={'quantity_on_hand': 100}
        )

    def test_ingredient_create(self):
        url = reverse('inventory:ingredient_add')
        data = {
            'sku': 'ING-002',
            'name': 'Sugar',
            'unit': 'kg',
            'cost_per_unit': 15.0,
            'alert_threshold': 10
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('inventory:ingredient_list'))
        self.assertTrue(Ingredient.objects.filter(sku='ING-002').exists())

    def test_adjust_stock(self):
        url = reverse('inventory:adjust_stock', args=[self.inv_item.pk])
        data = {
            'quantity': 120,
            'reason': 'Found extra bag'
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('inventory:dashboard'))
        
        self.inv_item.refresh_from_db()
        self.assertEqual(self.inv_item.quantity_on_hand, 120)
        
        # Verify Log
        log = InventoryLog.objects.latest('created_at')
        self.assertEqual(log.change_type, 'ADJUSTMENT')
        self.assertEqual(log.quantity_change, 20)

    def test_stock_take_flow(self):
        # 1. Start Stock Take
        create_url = reverse('inventory:stock_take_create')
        # Empty POST means create default? Or form needs data?
        # Form has code/notes. Code is auto-gen in view if not provided?
        # Looking at view: if form.is_valid(). Ticket form might have required fields?
        # Assuming notes is optional.
        response = self.client.post(create_url, {'notes': 'Monthly Audit'})
        
        if response.status_code == 200:
             # Form error?
             print(response.context['form'].errors)
        
        # Should redirect to details
        ticket = StockTakeTicket.objects.latest('created_at')
        self.assertRedirects(response, reverse('inventory:stock_take_detail', args=[ticket.ticket_id]))
        
        # Verify Snapshot
        detail = StockTakeDetail.objects.get(ticket=ticket, ingredient=self.ingredient)
        self.assertEqual(detail.snapshot_quantity, 100) # From setUp

        # 2. Input Actual Counts
        detail_url = reverse('inventory:stock_take_detail', args=[ticket.ticket_id])
        # ManagementForm data needed for formset
        data = {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000,
            'form-0-id': detail.id,
            'form-0-ticket': ticket.ticket_id, # Might be hidden/excluded
            'form-0-ingredient': self.ingredient.id, # Might be readonly
            'form-0-snapshot_quantity': 100,
            'form-0-actual_quantity': 95, # Variance -5
            'form-0-notes': 'Spilled',
            'finalize': 'Finalize' # Button click
        }
        response = self.client.post(detail_url, data)
        self.assertRedirects(response, reverse('inventory:stock_take_list'))
        
        # 3. Verify Finalization
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'COMPLETED')
        self.inv_item.refresh_from_db()
        self.assertEqual(self.inv_item.quantity_on_hand, 95)
