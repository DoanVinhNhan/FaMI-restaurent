from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from menu.models import MenuItem, Category, Pricing
from sales.models import RestaurantTable
from datetime import date

User = get_user_model()

class MenuViewTest(TestCase):
    def setUp(self):
        # Create User
        self.user = User.objects.create_user(username='manager', password='password')
        self.client = Client()
        self.client.login(username='manager', password='password')
        
        # Create Category
        self.category = Category.objects.create(name="Main Course", printer_target="KITCHEN")

    def test_menu_create_view(self):
        """test creating a menu item via view"""
        url = reverse('menu:menu_create')
        data = {
            'sku': 'NEW-001',
            'name': 'New Dish',
            'category': self.category.id,
            'description': 'Test Desc',
            'status': 'ACTIVE',
            'selling_price': '150000',
            'effective_date': date.today()
        }
        response = self.client.post(url, data)
        
        # Check success redirect
        self.assertRedirects(response, reverse('menu:menu_list'))
        
        # Verify DB
        item = MenuItem.objects.get(sku='NEW-001')
        self.assertEqual(item.name, 'New Dish')
        self.assertEqual(item.price, 150000)
        
        # Verify Pricing
        self.assertTrue(Pricing.objects.filter(menu_item=item, selling_price=150000).exists())

    def test_menu_edit_view(self):
        """test editing a menu item"""
        item = MenuItem.objects.create(sku='EDIT-001', name='Old Name', price=100, category=self.category)
        url = reverse('menu:menu_edit', args=[item.pk])
        
        data = {
            'sku': 'EDIT-001',
            'name': 'New Name',
            'category': self.category.id,
            'description': 'Updated',
            'status': 'ACTIVE'
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('menu:menu_list'))
        
        item.refresh_from_db()
        self.assertEqual(item.name, 'New Name')

    def test_menu_soft_delete_view(self):
        """test soft delete"""
        item = MenuItem.objects.create(sku='DEL-001', name='Delete Me', price=100, category=self.category, status='ACTIVE')
        url = reverse('menu:menu_delete', args=[item.pk])
        
        # GET shows confirm page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST performs delete
        response = self.client.post(url)
        self.assertRedirects(response, reverse('menu:menu_list'))
        
        item.refresh_from_db()
        self.assertEqual(item.status, 'INACTIVE')
