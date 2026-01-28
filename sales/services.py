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

        # 2. Apply Promotion (if any) - Calculate discount and capture promotion object
        discount = Decimal('0.00')
        promo_obj = None
        original_total = order.total_amount
        if promo_code:
            discount = PromotionEngine.apply_promotion(promo_code, order)
            try:
                promo_obj = Promotion.objects.get(promo_code=promo_code)
            except Promotion.DoesNotExist:
                promo_obj = None

            # Apply discount to order's total for compatibility (snapshot kept in Invoice)
            if discount > 0:
                order.total_amount -= discount
                if order.total_amount < 0:
                    order.total_amount = Decimal('0.00')
                order.save()

        # 3. Check Payment Amount
        final_required = max(Decimal('0.00'), original_total - discount)
        
        if amount < final_required:
            # Create a Failed Transaction Log (include promo info if present)
            Transaction.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                status=Transaction.PaymentStatus.FAILED,
                reference_code=f"FAILED-{timezone.now().timestamp()}",
                promotion=promo_obj,
                discount_amount=discount
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
            reference_code=gateway_ref,
            promotion=promo_obj,
            discount_amount=discount
        )

        # 6. Generate Invoice (snapshot promotion and discount)
        Invoice.objects.create(
            order=order,
            final_total=final_required, 
            payment_method=method,
            promotion=promo_obj,
            discount_amount=discount,
            original_total=original_total
        )

        # 7. Update Order Status
        order.status = Order.Status.PAID
        order.save()
        
        # 8. Deduct Inventory
        # Note: Inventory is deducted when Order is submitted to Kitchen (Status=Cooking).
        # We only deduct here if it wasn't deducted yet, but current view logic enforces Cooking status first.
        # Removing to prevent double deduction and fix AttributeError.
        # from inventory.services import InventoryService
        # try:
        #     if order.status == Order.Status.PENDING: # Should not happen with current strict view filtering
        #          InventoryService.deduct_ingredients_for_order(order)
        # except Exception as e:
        #     print(f"Inventory deduction failed: {e}")

        # 9. Print Receipt
        PaymentController.print_receipt(order, tx.pk)

        return {
            'success': True,
            'transaction_id': tx.pk,
            'message': u"Payment successful",
            'invoice_id': order.invoice.pk,
            'change': PaymentController.calculate_change(order, amount) if method == 'CASH' else 0
        }
