from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from sales.models import Promotion, DiscountType

User = get_user_model()

class ManagePromotionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='password')
        self.client.force_login(self.user)
        self.url_create = reverse('sales:promotion_create')
        self.url_list = reverse('sales:promotion_list')

    def test_create_promotion_success(self):
        data = {
            'name': 'New Year Sale',
            'promo_code': 'NY2026',
            'discount_type': DiscountType.PERCENTAGE,
            'discount_value': 20,
            'start_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'end_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': True
        }
        response = self.client.post(self.url_create, data)
        self.assertEqual(response.status_code, 302) # Redirects to list
        self.assertTrue(Promotion.objects.filter(promo_code='NY2026').exists())

    def test_validation_date_logic(self):
        # End Date < Start Date
        data = {
            'name': 'Bad Dates',
            'promo_code': 'BAD1',
            'discount_type': DiscountType.PERCENTAGE,
            'discount_value': 10,
            'start_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'end_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'), # Past
            'is_active': True
        }
        response = self.client.post(self.url_create, data)
        self.assertEqual(response.status_code, 200) # Form errors
        
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn("End date cannot be before start date.", form.non_field_errors())

    def test_validation_duplicate_code(self):
        Promotion.objects.create(
            name='Existing', promo_code='EXIST', 
            discount_type=DiscountType.FIXED_AMOUNT, discount_value=5,
            start_date=timezone.now(), end_date=timezone.now()+timedelta(days=1)
        )
        
        data = {
            'name': 'Duplicate',
            'promo_code': 'EXIST',
            'discount_type': DiscountType.FIXED_AMOUNT,
            'discount_value': 5,
            'start_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'end_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': True
        }
        response = self.client.post(self.url_create, data)
        self.assertEqual(response.status_code, 200)
        
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn("Promotion code 'EXIST' already exists.", form.errors['promo_code'])

    def test_edit_promotion(self):
        promo = Promotion.objects.create(
            name='Old Name', promo_code='EDITME', 
            discount_type=DiscountType.FIXED_AMOUNT, discount_value=5,
            start_date=timezone.now(), end_date=timezone.now()+timedelta(days=1)
        )
        
        url_edit = reverse('sales:promotion_edit', args=[promo.id])
        data = {
            'name': 'New Name',
            'promo_code': 'EDITME', # Same code allowed for self
            'discount_type': DiscountType.FIXED_AMOUNT, 
            'discount_value': 10,
            'start_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'end_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'is_active': True
        }
        response = self.client.post(url_edit, data)
        self.assertEqual(response.status_code, 302)
        
        promo.refresh_from_db()
        self.assertEqual(promo.name, 'New Name')
        self.assertEqual(promo.discount_value, 10)

    def test_delete_promotion(self):
        promo = Promotion.objects.create(
            name='To Delete', promo_code='DEL', 
            discount_type=DiscountType.FIXED_AMOUNT, discount_value=5,
            start_date=timezone.now(), end_date=timezone.now()+timedelta(days=1)
        )
        
        url_delete = reverse('sales:promotion_delete', args=[promo.id])
        response = self.client.post(url_delete) # DeleteView confirms via POST
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Promotion.objects.filter(id=promo.id).exists())
