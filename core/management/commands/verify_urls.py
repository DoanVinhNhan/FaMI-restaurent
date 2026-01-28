
import time

from django.core.management.base import BaseCommand
from django.urls import get_resolver, reverse
from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connection

# Models for ID resolution
from menu.models import MenuItem, Category
from inventory.models import Ingredient, StockTakeTicket
from sales.models import RestaurantTable, Order
from kitchen.models import WasteReport

User = get_user_model()

class Command(BaseCommand):
    help = 'Crawls and verifies all registered URLs in the system.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting Comprehensive URL Verification...'))
        
        # 1. Setup User
        user = self.get_or_create_superuser()
        client = Client()
        client.force_login(user)

        # 2. Pre-fetch Valid IDs for dynamic resolution
        self.ids = self.fetch_valid_ids()
        
        # 3. Discover URLs
        patterns = self.get_all_urls()
        self.stdout.write(f"Found {len(patterns)} URL patterns.")

        # 4. Verify Each
        results = {'pass': 0, 'fail': 0, 'warn': 0, 'skipped': 0}
        
        print(f"{'METHOD':<8} {'STATUS':<10} {'TIME':<10} {'URL'}")
        print("-" * 80)

        for name, args_type in patterns:
            # Skip admin and media/static for now to focus on app logic
            if name and (name.startswith('admin') or name.startswith('static') or name.startswith('media')):
                continue
                
            url = self.resolve_url(name, args_type)
            
            if not url:
                results['skipped'] += 1
                self.stdout.write(f"SKIPPED  ---        ---        {name} (Hint: {args_type})")
                continue

            try:
                start_time = time.time()
                response = client.get(url)
                duration = (time.time() - start_time) * 1000 # ms
                
                status_code = response.status_code
                
                status_code = response.status_code
                
                status_str = f"{status_code}"
                
                if status_code == 405:
                    style = self.style.WARNING
                    status_str += " MNA" # Method Not Allowed
                    results['pass'] += 1 # The URL exists and view is reachable
                elif status_code >= 400:
                    style = self.style.ERROR
                    results['fail'] += 1
                elif status_code >= 300:
                    style = self.style.WARNING
                    status_str += " R" # Redirect
                    results['pass'] += 1 # Redirects are usually okay (login required etc, but we are logged in)
                else:
                    style = self.style.SUCCESS
                    results['pass'] += 1
                
                # Check slowness
                if duration > 500:
                    status_str += " SLOW"
                    results['warn'] += 1
                    style = self.style.WARNING

                self.stdout.write(style(f"{'GET':<8} {status_str:<10} {int(duration)}ms     {url}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR    ERR        ---        {url} : {e}"))
                results['fail'] += 1

        self.stdout.write("-" * 80)
        self.stdout.write(f"Verification Complete.")
        self.stdout.write(f"Total: {sum(results.values())} | Pass: {results['pass']} | Fail: {results['fail']} | Warning: {results['warn']} | Skipped: {results['skipped']}")

    def get_or_create_superuser(self):
        try:
            return User.objects.get(username='url_tester')
        except User.DoesNotExist:
            return User.objects.create_superuser('url_tester', 'test@fami.local', 'password')

    def fetch_valid_ids(self):
        ids = {}
        ids['menu_item'] = MenuItem.objects.first().pk if MenuItem.objects.exists() else None
        ids['category'] = Category.objects.first().pk if Category.objects.exists() else None
        ids['ingredient'] = Ingredient.objects.first().pk if Ingredient.objects.exists() else None
        ids['table'] = RestaurantTable.objects.first().pk if RestaurantTable.objects.exists() else None
        ids['order'] = Order.objects.first().pk if Order.objects.exists() else None
        ids['stock_ticket'] = StockTakeTicket.objects.first().ticket_id if StockTakeTicket.objects.exists() else None
        ids['waste'] = WasteReport.objects.first().pk if WasteReport.objects.exists() else None
        return ids

    def get_all_urls(self):
        url_list = []
        resolver = get_resolver()
        
        def recursive_crawl(urlpatterns, prefix=''):
            for pattern in urlpatterns:
                if hasattr(pattern, 'url_patterns'):
                    # It's an include
                    new_prefix = prefix
                    if hasattr(pattern, 'namespace') and pattern.namespace:
                         new_prefix = f"{prefix}:{pattern.namespace}" if prefix else pattern.namespace
                    recursive_crawl(pattern.url_patterns, new_prefix)
                elif hasattr(pattern, 'name') and pattern.name:
                    # It's a view
                    full_name = f"{prefix}:{pattern.name}" if prefix else pattern.name
                    # Determine required args (naive)
                    # We will try to reverse it, if it fails, we know it needs args
                    url_list.append((full_name, str(pattern.pattern)))
        
        recursive_crawl(resolver.url_patterns)
        return url_list

    def resolve_url(self, name, pattern_str_hint):
        """
        Attempt to reverse the URL with intelligent parameter guessing.
        """
        try:
            return reverse(name)
        except Exception:
            pass # Needs args

        # Try mapping based on name or app context
        kwargs = {}
        
        # Menu App
        if 'menu' in name:
            if 'pk' in pattern_str_hint or 'id' in pattern_str_hint:
                if self.ids['menu_item']: kwargs['pk'] = self.ids['menu_item']
        
        # Inventory App
        elif 'inventory' in name:
            if 'stocktake' in name and ('uuid' in pattern_str_hint or 'ticket_id' in pattern_str_hint):
                 if self.ids['stock_ticket']: kwargs['ticket_id'] = self.ids['stock_ticket']
            elif 'pk' in pattern_str_hint or 'id' in pattern_str_hint:
                if self.ids['ingredient']: kwargs['pk'] = self.ids['ingredient']

        # Sales App
        elif 'sales' in name:
            if 'table' in name and ('pk' in pattern_str_hint or 'table_id' in pattern_str_hint):
                if self.ids['table']: kwargs['pk'] = self.ids['table'] # generic generic view uses pk, function might use table_id
                # Attempt dual keys if unsure? No, map explicitly if simple fail.
            elif 'pos' in name:
                 if 'table_id' in pattern_str_hint and self.ids['table']: kwargs['table_id'] = self.ids['table']
        
        # Kitchen App
        elif 'kitchen' in name:
            pass # Most kitchen views are list or generic, let's see

        # Reporting
        # Usually no args

        # Try reversing with guessed kwargs
        if not kwargs:
             # Try generic Primary Keys if nothing else matched but pattern looks like it needs one
             if '<int:pk>' in pattern_str_hint:
                 # Last ditch effort: Try basic IDs. 
                 # This is risky as it might use the wrong ID type, but for a checker it's okay to fail resolving.
                 pass

        # Specific Fixes for known routes if generic logic failed
        if name == 'sales:pos_add_item':
             # needs table_id and item_id
             if self.ids['table'] and self.ids['menu_item']:
                 kwargs = {'table_id': self.ids['table'], 'item_id': self.ids['menu_item']}
        
        if name == 'sales:pos_item_update':
             # unlikely to hit purely via GET but let's try
             pass
        
        if name == 'kitchen:update_item_status':
             # needs detail_id (OrderDetail)
             if self.ids['order']: # We need an OrderDetail ID actually, but let's see if we can fetch one
                from sales.models import OrderDetail
                detail = OrderDetail.objects.first()
                if detail:
                    kwargs = {'detail_id': detail.id}
        
        if name == 'inventory:stock_take_detail':
            if self.ids['stock_ticket']: kwargs['ticket_id'] = self.ids['stock_ticket']

        if name == 'sales:pos_table_detail':
            if self.ids['table']: kwargs['table_id'] = self.ids['table']
            
        if name == 'sales:pos_remove_item':
             # This is likely an action URL, needs table_id and unique_id (or similar)
             # Checking urls.py for sales would confirm params: path('pos/table/<int:table_id>/remove/<uuid:unique_id>/', ...)
             pass 

        if name == 'sales:process_payment':
             # likely path('pos/table/<int:table_id>/payment/', ...)
             if self.ids['table']: kwargs['table_id'] = self.ids['table']

        if name == 'kitchen:api_item_status':
            # likely needs pk or similar
             pass 

        base_url = None
        try:
            base_url = reverse(name, kwargs=kwargs)
        except Exception:
            return None
        
        
        # Inject Query Params for Report Views to avoid 400s
        if 'reporting' in name and ('sales' in name or 'inventory' in name or 'waste' in name):
            import datetime
            today = datetime.date.today().strftime('%Y-%m-%d')
            if '?' not in base_url:
                base_url += f"?start_date={today}&end_date={today}"
        
        
        return base_url
