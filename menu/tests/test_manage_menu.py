from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.contrib.messages.storage.fallback import FallbackStorage
from menu.models import MenuItem, Category, Pricing
from menu.views import menu_item_update_view

User = get_user_model()

class ManageMenuTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username='admin', password='password')
        self.category = Category.objects.create(name='Food')
        
        self.item = MenuItem.objects.create(
            sku='ITEM-TEST', name='Test Item', category=self.category, price=Decimal('10.00'), status='ACTIVE'
        )
        Pricing.objects.create(menu_item=self.item, selling_price=Decimal('10.00'), effective_date=timezone.now())

    def test_update_price_creates_history(self):
        url = reverse('menu:menu_item_edit', args=[self.item.pk])
        
        # Change price to 15.00
        data = {
            'sku': 'ITEM-TEST',
            'name': 'Test Item',
            'category': self.category.pk,
            'description': '',
            'status': 'ACTIVE',
            'selling_price': '15.00',
            'effective_date': timezone.now().date()
        }
        
        request = self.factory.post(url, data)
        request.user = self.user
        # Session mock
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Message mock
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, '_messages', FallbackStorage(request))

        response = menu_item_update_view(request, self.item.pk)
        
        self.assertEqual(response.status_code, 302)
        
        # Verify History
        self.assertEqual(Pricing.objects.filter(menu_item=self.item).count(), 2)
        latest = self.item.get_current_price()
        self.assertEqual(latest.selling_price, Decimal('15.00'))
        
        # Verify Display Price updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.price, Decimal('15.00'))

    def test_update_details_no_price_change(self):
        url = reverse('menu:menu_item_edit', args=[self.item.pk])
        
        # Keep price 10.00, change Name
        data = {
            'sku': 'ITEM-TEST',
            'name': 'Updated Name',
            'category': self.category.pk,
            'description': 'New Desc',
            'status': 'ACTIVE',
            'selling_price': '10.00',
            'effective_date': timezone.now().date()
        }
        
        request = self.factory.post(url, data)
        request.user = self.user
        # Mocks
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))

        response = menu_item_update_view(request, self.item.pk)
        
        self.assertEqual(response.status_code, 302)
        
        # Verify History count remains 1
        self.assertEqual(Pricing.objects.filter(menu_item=self.item).count(), 1)
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Updated Name')
