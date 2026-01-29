from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import SettingGroup, SystemSetting

User = get_user_model()

class ManageSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='password')
        self.client.force_login(self.user)
        
        self.group = SettingGroup.objects.create(group_name='General')
        self.setting = SystemSetting.objects.create(
            group=self.group,
            setting_key='TAX_RATE',
            setting_value='10',
            data_type=SystemSetting.DataType.INTEGER
        )

    def test_list_settings(self):
        url = reverse('core:setting_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TAX_RATE')
        self.assertContains(response, '10')

    def test_update_setting(self):
        url = reverse('core:setting_edit', args=['TAX_RATE'])
        
        # Update to 15
        data = {
            'setting_value': '15',
            'is_active': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect
        
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.setting_value, '15')

    def test_create_group_and_setting_via_frontend(self):
        # Create a new group via the create view
        group_url = reverse('core:setting_group_create')
        resp = self.client.post(group_url, {'group_name': 'Payments', 'description': 'Payment settings'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SettingGroup.objects.filter(group_name='Payments').exists())

        # Create a new setting via the create view
        group = SettingGroup.objects.get(group_name='Payments')
        setting_url = reverse('core:setting_create')
        data = {
            'setting_key': 'PAYMENT_GATEWAY',
            'setting_value': 'Stripe',
            'data_type': 'STRING',
            'group': group.pk,
            'is_active': True
        }
        resp2 = self.client.post(setting_url, data)
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(SystemSetting.objects.filter(setting_key='PAYMENT_GATEWAY').exists())

    def test_create_setting_permission_denied_for_cashier(self):
        # Login as cashier and attempt to access create views
        user = User.objects.create_user(username='c', password='p', role='CASHIER')
        self.client.force_login(user)

        group_url = reverse('core:setting_group_create')
        resp = self.client.get(group_url)
        # Expect redirect to access denied or similar (302)
        self.assertIn(resp.status_code, (302, 403))

        setting_url = reverse('core:setting_create')
        resp2 = self.client.get(setting_url)
        self.assertIn(resp2.status_code, (302, 403))
