
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class UIWalkerTestCase(TestCase):
    def setUp(self):
        # Create a Superuser to access everything
        self.user = User.objects.create_superuser('ui_tester', 'ui@test.com', 'testpass123')
        self.client = Client()
        self.client.login(username='ui_tester', password='testpass123')

    def test_all_pages_render(self):
        """
        Walks through all major pages to ensure they render (HTTP 200).
        """
        pages = [
            # Core
            ('core:dashboard', None),
            
            # Inventory
            ('inventory:ingredient_list', None),
            ('inventory:stock_take_list', None),
            
            # Menu
            ('menu:menu_list', None),
            
            # Sales
            ('sales:table_list', None),
            ('sales:pos_index', None),
            
            # Kitchen
            ('kitchen:kds_board', None),
            ('kitchen:waste_report', None),
            
            # Reporting
            ('reporting:dashboard', None),
        ]

        print("\n>>> STARTING UI PAGE VERIFICATION")
        for url_name, kwargs in pages:
            try:
                url = reverse(url_name, kwargs=kwargs)
                response = self.client.get(url)
                
                status_code = response.status_code
                if status_code == 200:
                    print(f"[OK] {url}: 200 OK")
                elif status_code == 302:
                    print(f"[OK] {url}: 302 Redirect (Accepted)")
                else:
                    print(f"[FAIL] {url}: {status_code}")
                    self.fail(f"Page {url} returned {status_code}")
                    
            except Exception as e:
                print(f"[ERROR] Could not resolve or visit {url_name}: {e}")
                self.fail(f"Error visiting {url_name}: {e}")

        print(">>> UI VERIFICATION COMPLETED")
