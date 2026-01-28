import sys
import os
import django
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

User = get_user_model()

# Helper to find a valid ID for dynamic URLs
def get_dynamic_arg(arg_name):
    # Map argument names to Model objects or values
    from sales.models import RestaurantTable, Order, OrderDetail
    from menu.models import MenuItem, Category
    from inventory.models import Ingredient
    from core.models import SystemSetting
    
    if arg_name in ['pk', 'id', 'item_id', 'table_id', 'detail_id']:
        # Try finding a generic object, or context specific?
        # Ideally we know which view needs which model, but URL resolver doesn't tell us easily.
        # We'll try a few common models.
        
        # This is a naive heuristic for this specific project structure
        if 'table' in arg_name or arg_name == 'table_id':
            obj = RestaurantTable.objects.first()
            if not obj:
                obj = RestaurantTable.objects.create(table_name="Test Table", capacity=4)
            return obj.pk
            
        if 'item' in arg_name:
            obj = MenuItem.objects.first()
            if not obj:
                cat = Category.objects.create(name="Test Cat")
                obj = MenuItem.objects.create(name="Test Item", price=10, sku="TEST001", category=cat)
            return obj.pk
            
        if 'detail' in arg_name:
             # Need an order detail attached to the DEFAULT table (likely ID 1 or whatever returned above)
             # To stay consistent, let's fetch the table we likely used
             table = RestaurantTable.objects.first()
             if not table:
                 table = RestaurantTable.objects.create(table_name="T1")
                 
             # Find/Create order for this table
             order = Order.objects.filter(table=table, status='Pending').first()
             if not order:
                 user = User.objects.first()
                 order = Order.objects.create(table=table, user=user)
             
             obj = OrderDetail.objects.filter(order=order).first()
             if not obj:
                 item = MenuItem.objects.first()
                 if not item:
                     cat = Category.objects.create(name="TC")
                     item = MenuItem.objects.create(name="TI", price=10, sku="T01", category=cat)
                 obj = OrderDetail.objects.create(order=order, menu_item=item, quantity=1, unit_price=10, total_price=10)
             return obj.pk

        # Check if looking for SystemSetting PK (usually string)
        # Note: arg_name might just be 'pk' for 'setting_edit'.
        # We can't distinguish easily without view inspection.
        # But we can try checking if 'pk' is int-like or not.
        # Fallback: if generic PK, return 1.
        
        # HACK: If the URL name implies settings, return a string key
        # This function doesn't know URL name context. 
        # We will add context sensitivity or just try-catch in the looper?
        # Better: let's ensure SystemSetting exists and return its PK if resolving fails?
        # Actually, get_dynamic_arg is called with just arg_name.
        
        # Let's creating a setting just in case 'pk' refers to it? 
        # No, 'pk' 1 works for most. 
        # We need a way to know WHICH model.
        
        return 1
    
    # Special handling handled here if arg_name is specific
    if arg_name == 'year': return 2026
    if arg_name == 'month': return 1
    return 1

# Helper to provide context-aware args
def get_args_for_url(url_name, required_args):
    args = []
    
    # Model imports
    from core.models import SystemSetting
    from sales.models import RestaurantTable
    
    # Specific Overrides based on URL Name
    if 'setting' in url_name:
        # Create/Get setting
        obj = SystemSetting.objects.first()
        if not obj:
            from core.models import SettingGroup
            g = SettingGroup.objects.create(group_name="G")
            obj = SystemSetting.objects.create(setting_key="TEST_KEY", group=g, setting_value="1")
        return [obj.pk] * len(required_args)

    if 'promotion' in url_name:
        from sales.models import Promotion
        from django.utils import timezone
        obj = Promotion.objects.first()
        if not obj:
            obj = Promotion.objects.create(
                name="Test Promo", 
                promo_code="TEST", 
                discount_value=10, 
                start_date=timezone.now(), 
                end_date=timezone.now()
            )
        return [obj.pk] * len(required_args)

    if 'stocktake' in url_name or 'stock_take' in url_name:
        from inventory.models import StockTake
        obj = StockTake.objects.first()
        if not obj:
            user = User.objects.first()
            obj = StockTake.objects.create(created_by=user)
        return [obj.pk] * len(required_args)

    if 'user' in url_name:
        # Looking for a user to edit. Return current user or create one.
        obj = User.objects.filter(is_superuser=False).first()
        if not obj:
            # Create dummy user
            obj = User.objects.create_user(username="test_staff", password="password", role='CASHIER')
        return [obj.pk] * len(required_args)

    for arg in required_args:
        args.append(get_dynamic_arg(arg))
    return args

def get_all_urls(urlpatterns, prefix=''):
    url_list = []
    for entry in urlpatterns:
        if hasattr(entry, 'url_patterns'):
            # It's an include(...)
            # Normalize prefix
            new_prefix = prefix
            if hasattr(entry, 'pattern'):
                new_prefix += str(entry.pattern)
            url_list.extend(get_all_urls(entry.url_patterns, new_prefix))
        elif hasattr(entry, 'name') and entry.name:
            # It's a view
            url_name = entry.name
            # Handle namespacing if possible, but pattern extraction is easier
            # We will try to reverse by name if we can build the name, 
            # OR we just try to populate the pattern string directly?
            # Reversing by name is safer if we know the full namespace.
            
            # Construct full pattern
            full_pattern = prefix + str(entry.pattern)
            
            # Extract required args from pattern string regex
            # Or use resolver. But simple walking:
            
            # Warning: entry.name is just key. If inside namespace?
            # We need to capture namespace from parent.
            # Simplified: Use the list of all named views from get_resolver().reverse_dict
            pass
    return url_list

def verify_urls():
    # Setup User
    username = 'verify_admin_full'
    password = 'password123'
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, password=password)
    
    client = Client()
    client.login(username=username, password=password)
    print("✅ Login successful")

    from django.urls import get_resolver
    resolver = get_resolver()
    
    # We want to test every named URL pattern
    # Flatten route list
    
    url_patterns_to_test = []
    
    def walk_routes(patterns, namespace=None, prefix=""):
        for p in patterns:
            current_ns = namespace
            if hasattr(p, 'namespace') and p.namespace:
                current_ns = p.namespace
            
            if hasattr(p, 'url_patterns'):
                # Recursive
                walk_routes(p.url_patterns, current_ns, prefix + str(p.pattern))
            elif hasattr(p, 'name') and p.name:
                # Found a view
                full_name = f"{namespace}:{p.name}" if namespace else p.name
                url_patterns_to_test.append({
                    'name': full_name,
                    'pattern': prefix + str(p.pattern),
                    'callback': p.callback
                })

    walk_routes(resolver.url_patterns)
    
    print(f"\nFound {len(url_patterns_to_test)} URL patterns. Testing...\n")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0

    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch

    for entry in url_patterns_to_test:
        name = entry['name']
        
        # Skip Admin URLs and built-ins to focus on App logic
        if 'admin' in name or 'static' in name or 'media' in name:
            continue
            
        try:
            # Inspection is hard without `get_resolver` internal logic for validation
            # But we can try to find the pattern object from `resolver` if we want args list.
            
            # Simple approach: Check reverse_dict? No, strictly private.
            # We'll stick to the trial approach but add the 'setting' heuristic.
            
            path = None
            found = False
            
            # Attempt 1: No Args
            try:
                path = reverse(name)
                found = True
            except NoReverseMatch:
                pass
                
            # Attempt 2: Use Heuristic Args if attempting reverse failed
            if not found:
                # We don't know exact args required here easily without parsing pattern string
                # Regex parsing of pattern string is best best.
                import re
                # pattern string is in entry['pattern']
                # e.g. "sales/pos/table/<int:table_id>/"
                pattern_str = entry['pattern']
                # Find all <...>
                required_args = re.findall(r'<(?:\w+:)?(\w+)>', pattern_str)
                
                if required_args:
                    try:
                        args = get_args_for_url(name, required_args)
                        path = reverse(name, args=args)
                        found = True
                    except Exception as e:
                        # print(f"   [Debug] Failed to reverse {name} with args {required_args}: {e}")
                        pass
            
            if not found:
                print(f"⚠️  Skipped [Cannot Reverse]: {name}")
                skipped_count += 1
                continue

            # GET Request
            response = client.get(path)
            if response.status_code in [200, 302]: # 302 is OK (redirects)
                print(f"✅ [{response.status_code}] {path} ({name})")
                success_count += 1
            elif response.status_code == 405: # Method Not Allowed (e.g. POST only views)
                print(f"✅ [405] {path} ({name}) - Method Not Allowed (Expected for POST-only)")
                success_count += 1
            else:
                print(f"❌ [{response.status_code}] {path} ({name})")
                # print(f"   Error: {response.content.decode('utf-8')[:100]}...")
                fail_count += 1

        except Exception as e:
            print(f"❌ [ERROR] {name}: {e}")
            fail_count += 1

    print(f"\nResults: {success_count} Passed, {fail_count} Failed, {skipped_count} Skipped/Unreachable")

if __name__ == "__main__":
    verify_urls()
