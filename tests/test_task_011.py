import os
import sys
import django
from decimal import Decimal

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from menu.models import MenuItem, Recipe, RecipeIngredient, Category
from inventory.models import Ingredient

def run_verification():
    print(">>> STARTING TASK 011 VERIFICATION (Recipe/BOM)")

    # 1. Setup Data: Ingredients
    # Clean up
    RecipeIngredient.objects.all().delete()
    Recipe.objects.all().delete()

    flour, _ = Ingredient.objects.get_or_create(
        sku="ING-FLOUR",
        defaults={'name': 'Flour', 'unit': 'g', 'cost_per_unit': 0.05} # 50 VND per gram
    )
    # Ensure cost is set correctly if it existed
    flour.cost_per_unit = 0.05
    flour.save()

    sugar, _ = Ingredient.objects.get_or_create(
        sku="ING-SUGAR",
        defaults={'name': 'Sugar', 'unit': 'g', 'cost_per_unit': 0.10} # 100 VND per gram
    )
    sugar.cost_per_unit = 0.10
    sugar.save()

    # 2. Setup Data: Menu Item
    cat, _ = Category.objects.get_or_create(name="Bakery")
    cake, _ = MenuItem.objects.get_or_create(
        sku="CAKE-001",
        defaults={'name': 'Basic Cake', 'category': cat, 'price': 50000}
    )

    # 3. Create Recipe
    print("Test 1: Creating Recipe...")
    recipe = Recipe.objects.create(
        menu_item=cake,
        instructions="Mix flour and sugar. Bake."
    )
    print(f"PASS: Created Recipe for {recipe.menu_item}")

    # 4. Add Ingredients
    print("Test 2: Adding Ingredients...")
    # 200g Flour * 0.05 = 10.00
    RecipeIngredient.objects.create(recipe=recipe, ingredient=flour, quantity=200, unit='g')
    # 100g Sugar * 0.10 = 10.00
    RecipeIngredient.objects.create(recipe=recipe, ingredient=sugar, quantity=100, unit='g')
    
    count = recipe.ingredients.count()
    if count == 2:
        print(f"PASS: Recipe has {count} ingredients")
    else:
        print(f"FAIL: Expected 2 ingredients, got {count}")

    # 5. Calculate Standard Cost
    print("Test 3: Calculating Standard Cost...")
    # Expected: (200 * 0.05) + (100 * 0.10) = 10 + 10 = 20.00
    cost = recipe.calculate_standard_cost()
    print(f"INFO: Calculated Standard Cost: {cost}")
    
    if abs(cost - 20.0) < 0.01:
        print("PASS: Cost calculation correct (20.0)")
    else:
        print(f"FAIL: Expected 20.0, got {cost}")

    print(">>> TASK 011 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_verification()
