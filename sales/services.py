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
    @transaction.atomic
    def process_payment(order_id: int, amount: Decimal, method: str, promo_code: str = None) -> dict:
        """
        Process a payment for an order.
        
        Args:
            order_id (int): ID of the order.
            amount (Decimal): Payment amount.
            method (str): Payment method (CASH, CARD, QR).
            promo_code (str): Optional promotion code.
            
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

        # 2. Apply Promotion (if any)
        discount = Decimal('0.00')
        if promo_code:
            discount = PromotionEngine.apply_promotion(promo_code, order)
            # We don't persist discount on Order model yet based on schema, 
            # ideally Order should have discount_amount field.
            # For now, we deduct from payable amount or assume 'total_amount' is final.
            # Strategy: We consider 'total_amount' as the subtotal in schema, 
            # but usually it's final. Let's assume we update total_amount OR 
            # we just accept less payment if discount covers it.
            
            # Better approach: Update order total to reflect discount
            # But we must be careful not to double apply if retrying.
            # For this 'simple' logic:
            pass 

        # Calculate final required
        final_required = order.total_amount - discount
        if final_required < 0: final_required = Decimal(0)

        # 3. Check Payment Amount
        # If CASH, user input amount. If Online, amount usually equals total.
        if amount < final_required:
            # Create a Failed Transaction Log
            tx = Transaction.objects.create(
                order=order,
                amount=amount,
                payment_method=method,
                status=Transaction.PaymentStatus.FAILED,
                reference_code=f"FAILED-{timezone.now().timestamp()}"
            )
            return {'success': False, 'transaction_id': tx.pk, 'message': f"Insufficient payment. Required: {final_required}"}

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
        # Update total to reflect what was actually paid/finalized if we applied discount
        if discount > 0:
            # This mutates the order total permanently
            order.total_amount = final_required 
            
        order.status = Order.Status.PAID
        order.save()
        
        # 8. Deduct Inventory
        from inventory.services import InventoryService
        InventoryService.deduct_for_order(order)

        return {
            'success': True,
            'transaction_id': tx.pk,
            'message': "Payment successful",
            'invoice_id': order.invoice.pk
        }
