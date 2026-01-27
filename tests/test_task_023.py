import os
import sys
import django
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from sales.models import Order, Invoice, Transaction
from sales.services import PaymentController

User = get_user_model()

def run_test():
    print(">>> STARTING TASK 023 VERIFICATION (Payment)")

    # 1. Setup Order
    user, _ = User.objects.get_or_create(username='payer_user')
    order = Order.objects.create(user=user, total_amount=Decimal('100.00'), status='PENDING')

    # 2. Test Partial Payment (Fail)
    print("Test 1: Insufficient Payment...")
    res = PaymentController.process_payment(order.id, Decimal('50.00'), 'CASH')
    assert res['success'] is False
    assert Transaction.objects.filter(order=order, status='FAILED').exists()
    print("PASS: Blocked insufficient payment")

    # 3. Test Successful Payment & Atomicity
    print("Test 2: Success Flow...")
    res = PaymentController.process_payment(order.id, Decimal('100.00'), 'CASH')
    
    # Check Result
    assert res['success'] is True
    
    # Check Order Status
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    
    # Check Invoice Snapshot
    assert hasattr(order, 'invoice')
    assert order.invoice.final_total == Decimal('100.00')
    
    # Check Transaction Log
    tx = Transaction.objects.get(pk=res['transaction_id'])
    assert tx.status == 'SUCCESS'

    print("PASS: Payment processed atomically (Order, Invoice, Tx updated)")

    print(">>> TASK 023 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
