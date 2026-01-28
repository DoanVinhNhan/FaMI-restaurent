from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from menu.models import MenuItem, Category


class KitchenOOSTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='kuser', password='pass')
        self.client.force_login(self.user)
        self.cat = Category.objects.create(name='Food')
        self.item = MenuItem.objects.create(sku='S-02', name='Test Item 2', price=5, category=self.cat, status=MenuItem.ItemStatus.ACTIVE)

    def test_mark_out_of_stock_endpoint(self):
        url = reverse('kitchen:mark_out_of_stock', args=[self.item.id])
        # Simulate HTMX/ AJAX request header
        resp = self.client.post(url, HTTP_HX_REQUEST='true')
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, MenuItem.ItemStatus.OUT_OF_STOCK)
        self.assertEqual(resp.status_code, 200)
