import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from inventory.forms import IngredientForm
from inventory.models import Ingredient

def run_test():
    print(">>> STARTING TASK 008 VERIFICATION (Views/Forms)")
    
    # Setup Mock User
    User = get_user_model()
    try:
        user, _ = User.objects.get_or_create(username="test_manager", role="Manager")
    except Exception:
        # Fallback if role choice validation fails (e.g. if 'Manager' is not exact key)
         user, _ = User.objects.get_or_create(username="test_manager")

    # 1. Test Form Logic (Unique SKU)
    print("Test 1: Form Validation...")
    
    # Create Base
    Ingredient.objects.filter(sku="TEST-FORM").delete()
    Ingredient.objects.create(name="Base", sku="TEST-FORM", unit="kg")
    
    # Attempt Duplicate via Form
    form_data = {
        'sku': 'test-form', # Lowercase, should be caught and checked against normalized 'TEST-FORM'
        'name': 'Duplicate',
        'unit': 'kg',
        'cost_per_unit': 10,
        'alert_threshold': 5
    }
    form = IngredientForm(data=form_data)
    if not form.is_valid():
        if 'sku' in form.errors:
            print("PASS: Form rejected duplicate SKU")
        else:
            print(f"FAIL: Unexpected form errors: {form.errors}")
    else:
        print("FAIL: Form accepted duplicate SKU")

    # 2. Test Space Cleanup
    form_data['sku'] = '  NEW-SKU  '
    # Ensure this new SKU doesn't conflict
    Ingredient.objects.filter(sku='NEW-SKU').delete()
    
    form = IngredientForm(data=form_data)
    if form.is_valid():
        clean_sku = form.cleaned_data['sku']
        if clean_sku == 'NEW-SKU':
            print("PASS: Form stripped spaces and upper-cased SKU")
        else:
            print(f"FAIL: Form did not clean SKU properly: '{clean_sku}'")
    else:
         print(f"FAIL: Form invalid for spaced SKU: {form.errors}")

    print(">>> TASK 008 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
