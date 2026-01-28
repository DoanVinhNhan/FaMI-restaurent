
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

# Models
from core.models import SystemSetting
from inventory.models import Ingredient, InventoryItem, StockTakeTicket, StockTakeDetail, InventoryLog
from menu.models import Category, MenuItem, Pricing, Recipe, RecipeIngredient
from sales.models import RestaurantTable, Order, OrderDetail

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with realistic Fast Food restaurant data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Wipe existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write("Cleaning existing data...")
            self.clean_data()
        
        self.stdout.write("Seeding data...")
        try:
            with transaction.atomic():
                self.create_users()
                self.create_ingredients()
                self.create_menu()
                self.create_tables()
                self.create_historical_orders()
                self.create_waste_logs()
            self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding data: {e}'))

    def clean_data(self):
        # Delete dependent first
        InventoryLog.objects.all().delete()
        StockTakeDetail.objects.all().delete()
        StockTakeTicket.objects.all().delete()
        OrderDetail.objects.all().delete()
        
        Order.objects.all().delete()
        RestaurantTable.objects.all().delete()
        RecipeIngredient.objects.all().delete()
        Recipe.objects.all().delete()
        Pricing.objects.all().delete()
        MenuItem.objects.all().delete()
        Category.objects.all().delete()
        InventoryItem.objects.all().delete()
        Ingredient.objects.all().delete()
        # User.objects.filter(is_superuser=False).delete() # Keep superuser

    def create_users(self):
        # Ensure we have a staff user
        if not User.objects.filter(username='cashier').exists():
            User.objects.create_user('cashier', 'cashier@fami.local', 'cashier123', role='CASHIER')
        if not User.objects.filter(username='manager').exists():
            User.objects.create_user('manager', 'manager@fami.local', 'manager123', role='MANAGER')
        if not User.objects.filter(username='kitchen').exists():
            User.objects.create_user('kitchen', 'kitchen@fami.local', 'kitchen123', role='KITCHEN')

    def create_ingredients(self):
        self.stdout.write("- Creating Ingredients...")
        self.ingredients = {} # Store for recipe linking
        
        data = [
            # Proteins
            ('Thịt Gà (Chicken)', 'kg', 60000), 
            ('Thịt Bò Xay (Ground Beef)', 'kg', 120000),
            ('Xúc Xích (Sausage)', 'kg', 80000),
            
            # Carbs
            ('Khoai Tây (Potato)', 'kg', 20000), 
            ('Bột Mì (Flour)', 'kg', 15000),
            ('Vỏ Bánh Burger', 'cái', 3000),
            
            # Veggies
            ('Rau Xà Lách', 'kg', 30000), 
            ('Cà Chua', 'kg', 25000), 
            ('Dưa Leo', 'kg', 20000),
            ('Hành Tây', 'kg', 15000),
            
            # Condiments/Oils
            ('Dầu Ăn', 'l', 45000), 
            ('Tương Cà', 'l', 35000), 
            ('Tương Ớt', 'l', 35000), 
            ('Mayonnaise', 'l', 60000),
            ('Phô Mai Lát', 'miếng', 5000),
            
            # Drinks
            ('Coca Cola Syrup', 'l', 40000), # Post-mix
            ('Pepsi Syrup', 'l', 40000),
            ('Ly Giấy', 'cái', 500),
        ]

        for name, unit, cost in data:
            ing, created = Ingredient.objects.get_or_create(
                sku=f"ING-{name[:3].upper()}-{random.randint(100,999)}",
                defaults={
                    'name': name,
                    'unit': unit,
                    'cost_per_unit': Decimal(cost),
                    'alert_threshold': 10
                }
            )
            
            # Create Inventory Item logic
            InventoryItem.objects.update_or_create(
                ingredient=ing,
                defaults={
                    'quantity_on_hand': Decimal(random.randint(50, 200)),
                    'storage_location': 'Main Kitchen'
                }
            )
            self.ingredients[name] = ing

    def create_menu(self):
        self.stdout.write("- Creating Menu & Recipes...")
        
        # Categories
        cat_food, _ = Category.objects.get_or_create(
            name='Đồ Ăn (Food)', defaults={'printer_target': 'KITCHEN'}
        )
        cat_drink, _ = Category.objects.get_or_create(
            name='Đồ Uống (Drink)', defaults={'printer_target': 'BAR'}
        )
        cat_snack, _ = Category.objects.get_or_create(
            name='Ăn Vặt (Snack)', defaults={'printer_target': 'KITCHEN'}
        )
        # Pre-create a dedicated Combo category for future combo items
        self.stdout.write("- Ensuring 'Combo' category exists...")
        cat_combo, _ = Category.objects.get_or_create(
            name='Combo',
            defaults={'printer_target': 'KITCHEN'}
        )

        menu_data = [
            # Main Courses
            {'name': 'Gà Rán (1 Miếng)', 'cat': cat_food, 'price': 35000, 
             'recipe': [('Thịt Gà (Chicken)', 0.15), ('Bột Mì (Flour)', 0.05), ('Dầu Ăn', 0.02)]},
            {'name': 'Combo Gà Rán (2 Miếng)', 'cat': cat_food, 'price': 65000, 
             'recipe': [('Thịt Gà (Chicken)', 0.30), ('Bột Mì (Flour)', 0.10), ('Dầu Ăn', 0.04)]},
            {'name': 'Burger Bò Phô Mai', 'cat': cat_food, 'price': 55000, 
             'recipe': [('Vỏ Bánh Burger', 1), ('Thịt Bò Xay (Ground Beef)', 0.1), ('Phô Mai Lát', 1), ('Rau Xà Lách', 0.02), ('Cà Chua', 0.02)]},
            {'name': 'Burger Gà Giòn', 'cat': cat_food, 'price': 50000, 
             'recipe': [('Vỏ Bánh Burger', 1), ('Thịt Gà (Chicken)', 0.1), ('Bột Mì (Flour)', 0.03), ('Mayonnaise', 0.01)]},
             
            # Snacks
            {'name': 'Khoai Tây Chiên (L)', 'cat': cat_snack, 'price': 35000, 
             'recipe': [('Khoai Tây (Potato)', 0.2), ('Dầu Ăn', 0.05)]},
             {'name': 'Khoai Tây Chiên (M)', 'cat': cat_snack, 'price': 25000, 
             'recipe': [('Khoai Tây (Potato)', 0.15), ('Dầu Ăn', 0.03)]},
             {'name': 'Xúc Xích Đức', 'cat': cat_snack, 'price': 25000, 
             'recipe': [('Xúc Xích (Sausage)', 0.1), ('Dầu Ăn', 0.01)]},

            # Drinks
            {'name': 'Coca Cola Tươi (L)', 'cat': cat_drink, 'price': 20000, 
             'recipe': [('Coca Cola Syrup', 0.05), ('Ly Giấy', 1)]}, # diluted
            {'name': 'Pepsi Tươi (L)', 'cat': cat_drink, 'price': 20000, 
             'recipe': [('Pepsi Syrup', 0.05), ('Ly Giấy', 1)]},
        ]
        
        self.menu_items = []

        for data in menu_data:
            item, _ = MenuItem.objects.get_or_create(
                sku=f"MENU-{random.randint(1000,9999)}",
                defaults={
                    'name': data['name'],
                    'category': data['cat'],
                    'description': f"Delicious {data['name']}",
                    'price': Decimal(data['price']),
                    'status': MenuItem.ItemStatus.ACTIVE
                }
            )
            
            # --- IMAGE LINKING LOGIC ---
            import os
            import unicodedata
            
            # Path to images relative to project root / media
            # Assuming seed_data run from project root context
            # We strictly link strings like 'menu_items/filename.png'
            
            # 1. Normalize Item Name
            clean_name = data['name'].split('(')[0].strip()
            slug_name = clean_name.replace(" ", "_").lower()
            expected_name = unicodedata.normalize('NFC', slug_name + ".png")
            
            # 2. Scan Directory (Once is better, but inside loop for simplicity of logic insertion)
            # Optimization: We can just construct the path and check if file exists in media_root
            from django.conf import settings
            media_root_menu = os.path.join(settings.MEDIA_ROOT, 'menu_items')
            
            found_filename = None
            if os.path.exists(media_root_menu):
                available_files = os.listdir(media_root_menu)
                # Normalize available files
                normalized_files = {unicodedata.normalize('NFC', f): f for f in available_files}
                
                # Match
                if expected_name in normalized_files:
                    found_filename = normalized_files[expected_name]
                elif ("ly_" + expected_name) in normalized_files:
                    found_filename = normalized_files["ly_" + expected_name]
                elif expected_name.startswith("ly_") and expected_name[3:] in normalized_files:
                    found_filename = normalized_files[expected_name[3:]]
                else:
                     # Fuzzy check
                     for norm_f, real_f in normalized_files.items():
                         if slug_name in norm_f:
                             found_filename = real_f
                             break
            
            if found_filename:
                # Direct Link String
                relative_path = os.path.join('menu_items', found_filename)
                item.image.name = relative_path
                item.save()
                self.stdout.write(f"  -> Linked Image: {relative_path}")
            # ---------------------------
            
            # Create Pricing
            Pricing.objects.create(
                menu_item=item,
                selling_price=Decimal(data['price']),
                effective_date=timezone.now() - timedelta(days=60)
            )
            
            # Create Recipe
            recipe, _ = Recipe.objects.get_or_create(menu_item=item)
            for ing_name, qty in data['recipe']:
                if ing_name in self.ingredients:
                    RecipeIngredient.objects.get_or_create(
                        recipe=recipe,
                        ingredient=self.ingredients[ing_name],
                        defaults={
                            'quantity': Decimal(qty),
                            'unit': self.ingredients[ing_name].unit
                        }
                    )
            
            self.menu_items.append(item)

    def create_tables(self):
        self.stdout.write("- Creating Tables...")
        self.tables = []
        
        # Room 1: Main Hall (1-10)
        for i in range(1, 11):
            t, _ = RestaurantTable.objects.get_or_create(
                table_name=f"Table {i}",
                defaults={'capacity': 4, 'status': 'AVAILABLE'}
            )
            self.tables.append(t)
            
        # Room 2: Garden (11-15)
        for i in range(11, 16):
            t, _ = RestaurantTable.objects.get_or_create(
                table_name=f"Outside {i}",
                defaults={'capacity': 6, 'status': 'AVAILABLE'}
            )
            self.tables.append(t)

    def create_historical_orders(self):
        self.stdout.write("- Simulating 30 days of sales...")
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        staff = User.objects.filter(role='STAFF').first() or User.objects.first()
        
        total_orders_created = 0
        
        for day in range(31):
            current_date = start_date + timedelta(days=day)
            
            weekday = current_date.weekday()
            if weekday >= 4:
                num_orders = random.randint(30, 50)
            else:
                num_orders = random.randint(15, 30)
                
            for _ in range(num_orders):
                hour = random.randint(10, 21)
                minute = random.randint(0, 59)
                order_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                table = random.choice(self.tables)
                
                order = Order.objects.create(
                    table=table,
                    user=staff,
                    status=Order.Status.PAID,
                    total_amount=0
                )
                
                num_items = random.randint(1, 6)
                items = random.choices(self.menu_items, k=num_items)
                
                order_total = Decimal(0)
                
                for item in items:
                    qty = random.randint(1, 2)
                    price = item.get_current_price().selling_price if item.get_current_price() else item.price
                    
                    detail = OrderDetail.objects.create(
                        order=order,
                        menu_item=item,
                        quantity=qty,
                        unit_price=price,
                        total_price=price * qty,
                        status='SERVED'
                    )
                    order_total += detail.total_price
                
                order.total_amount = order_total
                order.save()
                
                Order.objects.filter(pk=order.pk).update(created_at=order_time, updated_at=order_time)
                OrderDetail.objects.filter(order=order).update(created_at=order_time)
                
                total_orders_created += 1
                
        self.stdout.write(f"- Created {total_orders_created} historical orders.")

    def create_waste_logs(self):
        self.stdout.write("- Simulating Waste Logs...")
        from inventory.models import InventoryLog
        
        reasons = ['Spoiled', 'Expired', 'Dropped', 'Burnt', 'Quality Check']
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        total_waste = 0
        ingredients = list(self.ingredients.values())
        manager = User.objects.filter(role='MANAGER').first() or User.objects.first()
        
        for day in range(31):
            current_date = start_date + timedelta(days=day)
            
            # Randomly 1-3 waste events per day
            num_events = random.randint(1, 3)
            
            for _ in range(num_events):
                ing = random.choice(ingredients)
                qty = Decimal(random.uniform(0.1, 1.5)).quantize(Decimal('0.01'))
                
                log = InventoryLog.objects.create(
                    ingredient=ing,
                    user=manager,
                    change_type='WASTE',
                    quantity_change=-qty, # Negative for deduction
                    reason=random.choice(reasons),
                    # created_at handled below
                )
                # Manually set created_at 
                InventoryLog.objects.filter(pk=log.pk).update(created_at=current_date)
                
                total_waste += 1
                
        self.stdout.write(f"- Created {total_waste} waste records.")

