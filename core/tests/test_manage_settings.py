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
