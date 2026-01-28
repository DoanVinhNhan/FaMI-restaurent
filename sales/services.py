from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order, Invoice, Transaction, Promotion, DiscountType

class PromotionEngine:
    """
    Handles promotion logic (UC2).
    """
    @staticmethod
    def validate_code(code: str, order: Order) -> bool:
        """
        Validates if a promo code is applicable to the order.
        """
        if not code:
            return False
            
        try:
            promo = Promotion.objects.get(promo_code=code)
        except Promotion.DoesNotExist:
            return False
            
        if not promo.is_valid():
            return False
            
        # Optional: Check if order meets criteria (e.g. min total)
        # For now, just basic validation
        return True

    @staticmethod
    def apply_promotion(code: str, order: Order) -> Decimal:
        """
        Calculates the discount amount for a given code and order.
        Does NOT save the order, just returns the discount value.
        """
        try:
            promo = Promotion.objects.get(promo_code=code)
        except Promotion.DoesNotExist:
            return Decimal('0.00')
            
        if not promo.is_valid():
            return Decimal('0.00')
            
        discount_amount = Decimal('0.00')
        order_total = order.total_amount
        
        if promo.discount_type == DiscountType.PERCENTAGE:
             discount_amount = order_total * (promo.discount_value / Decimal('100.00'))
        else:
             discount_amount = promo.discount_value
             
        # Cap discount at order total
        if discount_amount > order_total:
            discount_amount = order_total
            
        return discount_amount

class PaymentGatewayClient:
    """
    Adapter for external Payment Gateway (VNPay, Momo).
    """
    @staticmethod
    def send_transaction(amount: Decimal, ref_id: str) -> dict:
        """
        Mock implementation of sending a transaction.
        In a real scenario, this would POST to an external API.
        """
        # Simulate Success/Fail based on some logic (e.g. amount ending in .99 fails)
        # For now, always success unless specified
        success = True
        gateway_ref = f"GW-{ref_id}-{timezone.now().timestamp()}"
        
        return {'success': success, 'gateway_ref': gateway_ref, 'message': 'Approved'}

    @staticmethod
    def verify_signature(response_data: dict) -> bool:
        # Stub for signature verification
        return True

class PaymentController:
    """
    Handles payment processing logic (UC7).
    Ensures atomicity between Order status update, Invoice generation, and Transaction logging.
    """
    @staticmethod
    def calculate_change(order: Order, cash_received: Decimal) -> Decimal:
        """
        Calculates change to return to customer.
        """
        return max(Decimal('0.00'), cash_received - order.total_amount)

    @staticmethod
    def print_receipt(order: Order, transaction_id: int = None) -> None:
        """
        Mock implementation of sending print job to a receipt printer.
        """
        # In a real system, this would queue a job for a CUPS server or ESC/POS printer
        print(f"[PRINTER] Printing Receipt for Order #{order.id}")
        if transaction_id:
            print(f"[PRINTER] Transaction Ref: {transaction_id}")
        print("--------------------------------")
        for detail in order.details.all():
            print(f"{detail.quantity}x {detail.menu_item.name} ... {detail.total_price}")
        print(f"TOTAL: {order.total_amount}")
        print("--------------------------------")

    @staticmethod
    @transaction.atomic
    def process_payment(order_id: int, amount: Decimal, method: str, promo_code: str = None) -> dict:
        """
        Process a payment for an order.
        """
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return {'success': False, 'message': "Order not found"}

        # 1. Validation
        if order.status == Order.Status.PAID:
            return {'success': False, 'message': "Order is already paid."}

        # 2. Apply Promotion (if any) - Assuming this is the FINAL step where we commit it
        discount = Decimal('0.00')
        if promo_code:
            discount = PromotionEngine.apply_promotion(promo_code, order)
            # Apply discount to total permanently for the invoice
            # Note: Ideally we should track 'original_total' and 'discount_applied'
            if discount > 0:
                order.total_amount -= discount
                if order.total_amount < 0:
                    order.total_amount = Decimal('0.00')
                order.save()

        # 3. Check Payment Amount
        final_required = order.total_amount
        
        if amount < final_required:
            # Create a Failed Transaction Log
            Transaction.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                status=Transaction.PaymentStatus.FAILED,
                reference_code=f"FAILED-{timezone.now().timestamp()}"
            )
            return {'success': False, 'transaction_id': None, 'message': f"Insufficient payment. Required: {final_required}"}

        # 4. Gateway Integration (if not CASH)
        gateway_ref = None
        if method != 'CASH':
            gw_response = PaymentGatewayClient.send_transaction(amount, f"ORDER-{order.id}")
            if not gw_response.get('success'):
                 return {'success': False, 'message': "Payment Gateway Rejected."}
            gateway_ref = gw_response.get('gateway_ref')

        # 5. Create Transaction (Success)
        tx = Transaction.objects.create(
            order=order,
            amount=amount,
            payment_method=method,
            status=Transaction.PaymentStatus.SUCCESS,
            reference_code=gateway_ref
        )

        # 6. Generate Invoice
        Invoice.objects.create(
            order=order,
            final_total=final_required, 
            payment_method=method
        )

        # 7. Update Order Status
        order.status = Order.Status.PAID
        order.save()
        
        # 8. Deduct Inventory
        from inventory.services import InventoryService
        try:
            InventoryService.deduct_for_order(order)
        except Exception as e:
            # Log error but don't fail payment
            print(f"Inventory deduction failed: {e}")

        # 9. Print Receipt
        PaymentController.print_receipt(order, tx.pk)

        return {
            'success': True,
            'transaction_id': tx.pk,
            'message': u"Payment successful",
            'invoice_id': order.invoice.pk,
            'change': PaymentController.calculate_change(order, amount) if method == 'CASH' else 0
        }
