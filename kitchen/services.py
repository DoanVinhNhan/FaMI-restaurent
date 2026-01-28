from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from sales.models import OrderDetail
from kitchen.models import StatusHistory
from core.services import NotificationService

User = get_user_model()

class KitchenController:
    """
    Controller logic for Kitchen operations.
    Handles state transitions, history logging, and notifications.
    """

    @staticmethod
    @transaction.atomic
    def update_item_status(
        order_detail_id: int, 
        new_status: str, 
        user
    ) -> OrderDetail:
        """
        Updates the status of an order item.
        """
        try:
            item = OrderDetail.objects.select_related('order', 'menu_item').get(pk=order_detail_id)
        except OrderDetail.DoesNotExist:
            raise ValidationError(f"OrderDetail with ID {order_detail_id} not found.")

        old_status = item.status

        # 1. Validation Logic
        # Allow reverting if needed, but generally enforce forward flow
        # If new_status is CANCELLED, we might need a separate method or allow it here
        
        # Simple State Machine validation could go here
        
        if old_status == new_status:
            return item

        # 2. Update Status
        item.status = new_status
        item.save()

        # 3. Log History
        StatusHistory.objects.create(
            order_detail=item,
            old_status=old_status,
            new_status=new_status,
            changed_by=user
        )

        # 4. Notifications
        item_name = item.menu_item.name if item.menu_item else "Unknown Item"
        
        if new_status == StatusHistory.OrderStatus.READY:
            NotificationService.send_ready_signal(
                order_id=item.order.id, 
                item_name=item_name
            )
        
        return item

    @staticmethod
    @transaction.atomic
    def cancel_item(order_detail_id: int, reason_code: str, user) -> OrderDetail:
        """
        Cancels an item with a reason.
        """
        try:
            item = OrderDetail.objects.select_related('order', 'menu_item').get(pk=order_detail_id)
        except OrderDetail.DoesNotExist:
            raise ValidationError(f"Item {order_detail_id} not found.")
            
        old_status = item.status
        if old_status == StatusHistory.OrderStatus.SERVED:
             raise ValidationError("Cannot cancel an item that has already been Served.")

        item.status = StatusHistory.OrderStatus.CANCELLED
        # Store reason in note or separate log? Using note for now or WasteReport if implicit
        if reason_code:
            item.note = f"{item.note or ''} [CANCELLED: {reason_code}]"
        
        item.save()
        
        StatusHistory.objects.create(
            order_detail=item,
            old_status=old_status,
            new_status=StatusHistory.OrderStatus.CANCELLED,
            changed_by=user
        )
        
        NotificationService.send_cancellation_alert(
            order_id=item.order.id,
            item_name=item.menu_item.name,
            reason=reason_code
        )
        return item

    @staticmethod
    @transaction.atomic
    def undo_last_status(order_detail_id: int, user) -> OrderDetail:
        """
        Reverts the item to its previous status based on history.
        """
        item = OrderDetail.objects.get(pk=order_detail_id)
        last_change = StatusHistory.objects.filter(order_detail=item).order_by('-changed_at').first()
        
        if not last_change:
            raise ValidationError("No history found to undo.")
            
        # Revert
        prev_status = last_change.old_status
        item.status = prev_status
        item.save()
        
        # Log the Undo action itself? 
        # Yes, standard practice: Old(Current) -> New(Previous)
        StatusHistory.objects.create(
            order_detail=item,
            old_status=last_change.new_status,
            new_status=prev_status,
            changed_by=user
        )
        
        return item

    @staticmethod
    def get_pending_items():
        """
        Retrieve items for KDS.
        Shows Pending, Cooking, and Ready (so they can be marked SERVED).
        """
        return OrderDetail.objects.filter(
            status__in=[
                StatusHistory.OrderStatus.PENDING, 
                StatusHistory.OrderStatus.COOKING,
                StatusHistory.OrderStatus.READY
            ]
        ).select_related('menu_item', 'order', 'order__table').order_by('order__created_at')
