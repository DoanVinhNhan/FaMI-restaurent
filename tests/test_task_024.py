import os
import sys
import django
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Ingredient, StockTakeTicket, StockTakeDetail

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 024 VERIFICATION (Stock Taking Models)")

    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='stock_manager')
    ing, _ = Ingredient.objects.get_or_create(
        sku='TEST-STACK-01', 
        defaults={'name': 'Stock Test Item', 'cost_per_unit': Decimal('10.00')}
    )

    # 2. Create Ticket
    ticket = StockTakeTicket.objects.create(
        code='ST-TEST-001',
        creator=user,
        status=StockTakeTicket.Status.DRAFT
    )
    print(f"PASS: Created Ticket {ticket.code}")

    # 3. Create Detail (Snapshot = 10, Actual = 8) -> Variance should be -2
    detail = StockTakeDetail.objects.create(
        ticket=ticket,
        ingredient=ing,
        snapshot_quantity=Decimal('10.00'),
        actual_quantity=Decimal('8.00')
    )
    
    # 4. Verify Variance Calculation (in save method)
    # Variance = Actual (8) - Snapshot (10) = -2
    if detail.variance == Decimal('-2.00'):
        print(f"PASS: Variance calculated correctly: {detail.variance}")
    else:
        print(f"FAIL: Variance invalid. Got {detail.variance}, expected -2.00")

    # 5. Verify Ticket Total Variance
    # Ticket Total = Sum of (Variance * Cost)
    #               = -2 * 10.00 = -20.00
    total_variance = ticket.calculate_total_variance()
    if total_variance == Decimal('-20.00'):
        print(f"PASS: Ticket Total Variance: {total_variance}")
    else:
        print(f"FAIL: Ticket Total Variance invalid. Got {total_variance}, expected -20.00")

    print(">>> TASK 024 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
