from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order, Invoice, Transaction

class PaymentController:
    """
    Handles payment processing logic (UC7).
    Ensures atomicity between Order status update, Invoice generation, and Transaction logging.
    """

    @staticmethod
    @transaction.atomic
    def process_payment(order_id: int, amount: Decimal, method: str) -> dict:
        """
        Process a payment for an order.
        
        Args:
            order_id (int): ID of the order.
            amount (Decimal): Payment amount.
            method (str): Payment method (CASH, CARD, QR).
            
        Returns:
            dict: { 'success': bool, 'transaction_id': int, 'message': str }
        """
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return {'success': False, 'message': "Order not found"}

        # 1. Validation
        if order.status == Order.Status.PAID:
            return {'success': False, 'message': "Order is already paid."}
        
        # Enforce full payment (Business Rule)
        # In future, partial payments might be allowed, but for now strict check.
        if amount < order.total_amount:
            # Create a Failed Transaction Log
            tx = Transaction.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                status=Transaction.PaymentStatus.FAILED
            )
            return {'success': False, 'transaction_id': tx.pk, 'message': "Insufficient payment amount."}

        # 2. Create Transaction (Success)
        tx = Transaction.objects.create(
            order=order,
            amount=amount,
            payment_method=method,
            status=Transaction.PaymentStatus.SUCCESS
        )

        # 3. Generate Invoice
        Invoice.objects.create(
            order=order,
            final_total=order.total_amount, # Using order total, ignoring overpayment (treated as tip or change)
            payment_method=method
        )

        # 4. Update Order Status
        order.status = Order.Status.PAID
        order.save()

        return {
            'success': True,
            'transaction_id': tx.pk,
            'message': "Payment successful",
            'invoice_id': order.invoice.pk
        }
