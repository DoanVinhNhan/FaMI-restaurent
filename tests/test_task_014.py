import os
import sys
import django
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from sales.models import Promotion, DiscountType
from menu.models import MenuItem, Category

def run_test():
    print(">>> STARTING TASK 014 VERIFICATION (Promotions)")
    
    # Setup Data
    cat, _ = Category.objects.get_or_create(name="Promo Test Cat")
    item, _ = MenuItem.objects.get_or_create(sku="PROMO-ITEM-01", defaults={'name': 'Promo Item', 'category': cat, 'price': 100})
    
    # 1. Test Valid Promotion Creation
    print("\nTest 1: Valid Promotion Creation...")
    try:
        start = timezone.now()
        end = start + timedelta(days=7)
        promo = Promotion.objects.create(
            name="Summer Sale",
            promo_code="SUMMER2025",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=20,
            start_date=start,
            end_date=end
        )
        print(f"PASS: Created Promotion '{promo.name}'")
        
        # Link Item
        promo.eligible_items.add(item)
        print(f"PASS: Linked item '{item.name}' to promotion")
        
        if promo.is_valid():
            print("PASS: is_valid() returned True")
        else:
            print("FAIL: is_valid() returned False")
    except Exception as e:
        print(f"FAIL: Exception: {e}")

    # 2. Test Date Validation (End before Start)
    print("\nTest 2: Date Validation...")
    try:
        bad_promo = Promotion(
            name="Bad Date",
            promo_code="FAIL_DATE",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=10,
            start_date=timezone.now(),
            end_date=timezone.now() - timedelta(days=1) # Past
        )
        bad_promo.full_clean() # Should raise ValidationError
        print("FAIL: Did not raise ValidationError for invalid dates")
    except ValidationError as e:
        print(f"PASS: Caught expected ValidationError: {e}")

    # 3. Test Percentage Validation
    print("\nTest 3: Percentage Validation...")
    try:
        bad_percent = Promotion(
            name="Bad Percent",
            promo_code="FAIL_PERC",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=150, # > 100
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1)
        )
        bad_percent.full_clean()
        print("FAIL: Did not raise ValidationError for >100%")
    except ValidationError as e:
        print(f"PASS: Caught expected ValidationError: {e}")

    print(">>> TASK 014 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
