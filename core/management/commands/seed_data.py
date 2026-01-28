
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
from inventory.models import Ingredient, InventoryItem
from menu.models import Category, MenuItem, Pricing, Recipe, RecipeIngredient
from sales.models import RestaurantTable, Order, OrderDetail

# cooking logic from sales/views.py? We just insert data directly.

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with realistic Vietnamese restaurant data.'

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
            self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding data: {e}'))

    def clean_data(self):
        # Delete dependent first
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
        if not User.objects.filter(username='staff').exists():
            User.objects.create_user('staff', 'staff@fami.local', 'staff123', role='STAFF')
        if not User.objects.filter(username='manager').exists():
            User.objects.create_user('manager', 'manager@fami.local', 'manager123', role='MANAGER')
        if not User.objects.filter(username='kitchen').exists():
            User.objects.create_user('kitchen', 'kitchen@fami.local', 'kitchen123', role='KITCHEN')

    def create_ingredients(self):
        self.stdout.write("- Creating Ingredients...")
        self.ingredients = {} # Store for recipe linking
        
        data = [
            # Proteins
            ('Thịt Bò (Beef)', 'kg', 250000), ('Thịt Gà (Chicken)', 'kg', 120000), 
            ('Thịt Heo (Pork)', 'kg', 150000), ('Tôm (Shrimp)', 'kg', 300000),
            # Carbs
            ('Gạo Thơm', 'kg', 25000), ('Bún Tươi', 'kg', 15000), ('Phở Tươi', 'kg', 18000),
            # Veggies
            ('Rau Xà Lách', 'kg', 30000), ('Cà Chua', 'kg', 25000), ('Dưa Leo', 'kg', 20000),
            ('Hành Tây', 'kg', 15000), ('Ngò Rí', 'kg', 50000), ('Ớt Hiểm', 'kg', 80000),
            # Spices/Sauces
            ('Nước Mắm', 'l', 50000), ('Đường Cát', 'kg', 22000), ('Muối Ăn', 'kg', 10000),
            ('Tiêu Đen', 'kg', 300000), ('Tương Ớt', 'l', 35000), ('Dầu Ăn', 'l', 45000),
            # Drinks
            ('Cafe Hạt', 'kg', 350000), ('Sữa Đặc', 'hop', 25000), ('Trà Đen', 'kg', 150000),
            ('Đường Nước', 'l', 20000), ('Sữa Tươi', 'l', 35000), ('Trân Châu', 'kg', 50000),
            ('Coca Cola', 'lon', 8000), ('Bia Tiger', 'lon', 12000),
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
        cat_food, _ = Category.objects.get_or_create(name='Món Ăn', defaults={'printer_target': 'KITCHEN'})
        cat_drink, _ = Category.objects.get_or_create(name='Đồ Uống', defaults={'printer_target': 'BAR'})
        cat_snack, _ = Category.objects.get_or_create(name='Ăn Vặt', defaults={'printer_target': 'KITCHEN'})

        menu_data = [
            # Food
            {'name': 'Phở Bò Đặc Biệt', 'cat': cat_food, 'price': 75000, 'cost': 35000, 
             'recipe': [('Phở Tươi', 0.2), ('Thịt Bò (Beef)', 0.15), ('Hành Tây', 0.05), ('Nước Mắm', 0.02)]},
            {'name': 'Phở Gà Ta', 'cat': cat_food, 'price': 65000, 'cost': 30000, 
             'recipe': [('Phở Tươi', 0.2), ('Thịt Gà (Chicken)', 0.15), ('Hành Tây', 0.05)]},
            {'name': 'Cơm Tấm Sườn Bì', 'cat': cat_food, 'price': 55000, 'cost': 25000, 
             'recipe': [('Gạo Thơm', 0.15), ('Thịt Heo (Pork)', 0.12), ('Dưa Leo', 0.05), ('Nước Mắm', 0.03)]},
            {'name': 'Bún Bò Huế', 'cat': cat_food, 'price': 70000, 'cost': 32000, 
             'recipe': [('Bún Tươi', 0.2), ('Thịt Bò (Beef)', 0.1), ('Thịt Heo (Pork)', 0.05)]},
            {'name': 'Mì Xào Bò', 'cat': cat_food, 'price': 60000, 'cost': 28000, 
             'recipe': [('Thịt Bò (Beef)', 0.1), ('Rau Xà Lách', 0.1)]},
             
            # Drinks
            {'name': 'Cafe Sữa Đá', 'cat': cat_drink, 'price': 35000, 'cost': 12000, 
             'recipe': [('Cafe Hạt', 0.02), ('Sữa Đặc', 1.0)]}, # 1 can? no 1 unit usually means something else but let's say 0.05 can
            {'name': 'Cafe Đen Đá', 'cat': cat_drink, 'price': 30000, 'cost': 10000, 
             'recipe': [('Cafe Hạt', 0.02), ('Đường Cát', 0.02)]},
            {'name': 'Trà Sữa Trân Châu', 'cat': cat_drink, 'price': 45000, 'cost': 15000, 
             'recipe': [('Trà Đen', 0.01), ('Sữa Tươi', 0.1), ('Trân Châu', 0.05), ('Đường Nước', 0.03)]},
            {'name': 'Nước Cam Ép', 'cat': cat_drink, 'price': 40000, 'cost': 18000, 'recipe': []},
            {'name': 'Coca Cola', 'cat': cat_drink, 'price': 20000, 'cost': 8000, 
             'recipe': [('Coca Cola', 1.0)]},
            {'name': 'Bia Tiger Bạc', 'cat': cat_drink, 'price': 25000, 'cost': 12000, 
             'recipe': [('Bia Tiger', 1.0)]},
             
             # Snacks
            {'name': 'Khoai Tây Chiên', 'cat': cat_snack, 'price': 35000, 'cost': 15000, 'recipe': []},
            {'name': 'Chả Giò (5 cuốn)', 'cat': cat_snack, 'price': 40000, 'cost': 18000, 
             'recipe': [('Thịt Heo (Pork)', 0.1), ('Bún Tươi', 0.05)]},
        ]
        
        self.menu_items = []

        for data in menu_data:
            item, _ = MenuItem.objects.get_or_create(
                sku=f"MENU-{random.randint(1000,9999)}",
                defaults={
                    'name': data['name'],
                    'category': data['cat'],
                    'description': f"Món ngon: {data['name']}",
                    'price': Decimal(data['price']), # Display price
                    'status': MenuItem.ItemStatus.ACTIVE
                }
            )
            
            # Create Pricing
            Pricing.objects.create(
                menu_item=item,
                selling_price=Decimal(data['price']),
                effective_date=timezone.now() - timedelta(days=60) # Effective from past
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
                table_name=f"Bàn {i}",
                defaults={'capacity': 4, 'status': 'AVAILABLE'}
            )
            self.tables.append(t)
            
        # Room 2: Garden (11-15)
        for i in range(11, 16):
            t, _ = RestaurantTable.objects.get_or_create(
                table_name=f"Sân Vườn {i}",
                defaults={'capacity': 6, 'status': 'AVAILABLE'}
            )
            self.tables.append(t)
            
        # Room 3: VIP (1-3)
        for i in range(1, 4):
            t, _ = RestaurantTable.objects.get_or_create(
                table_name=f"VIP {i}",
                defaults={'capacity': 10, 'status': 'AVAILABLE'}
            )
            self.tables.append(t)

    def create_historical_orders(self):
        self.stdout.write("- Simulating 30 days of sales (this may take a moment)...")
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # User for orders
        staff = User.objects.filter(role='STAFF').first() or User.objects.first()
        
        total_orders_created = 0
        
        for day in range(31): # 0 to 30
            current_date = start_date + timedelta(days=day)
            
            # More orders on weekends (Fri=4, Sat=5, Sun=6)
            weekday = current_date.weekday()
            if weekday >= 4:
                num_orders = random.randint(30, 50)
            else:
                num_orders = random.randint(15, 30)
                
            for _ in range(num_orders):
                # Random time within operating hours (10am - 10pm)
                hour = random.randint(10, 21)
                minute = random.randint(0, 59)
                order_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                table = random.choice(self.tables)
                
                # Create Order
                order = Order.objects.create(
                    table=table,
                    user=staff,
                    status=Order.Status.PAID, # Assume historical orders are paid
                    total_amount=0
                )
                # Hack: update created_at manually (since auto_now_add is usually read-only on create)
                # But Django auto_now_add sets it on save. We can update it with update()
                
                # Add Items
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
                        status='SERVED' # Delivered
                    )
                    order_total += detail.total_price
                
                order.total_amount = order_total
                order.save()
                
                # Force update timestamp in DB
                Order.objects.filter(pk=order.pk).update(created_at=order_time, updated_at=order_time)
                OrderDetail.objects.filter(order=order).update(created_at=order_time)
                
                total_orders_created += 1
                
        self.stdout.write(f"- Created {total_orders_created} historical orders.")

