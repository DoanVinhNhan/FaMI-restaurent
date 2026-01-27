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
        
        1. Validates the transition.
        2. Updates OrderDetail.
        3. Creates StatusHistory log.
        4. Triggers NotificationService if status is READY or CANCELLED.
        """
        try:
            item = OrderDetail.objects.select_related('order', 'menu_item').get(pk=order_detail_id)
        except OrderDetail.DoesNotExist:
            raise ValidationError(f"OrderDetail with ID {order_detail_id} not found.")

        old_status = item.status

        # 1. Basic Validation (Business Rules)
        # Prevent updates on already served or cancelled items (unless explicit undo logic is added)
        if old_status in [StatusHistory.OrderStatus.SERVED, StatusHistory.OrderStatus.CANCELLED]:
            # Allow Undo/Correction if user is admin or explicitly allowed (omitted for now)
            # For strictly enforced flow:
            raise ValidationError(f"Cannot update item that is already {old_status}.")
        
        if old_status == new_status:
            return item # No change needed

        # 2. Update Status
        item.status = new_status
        item.save()

        # 3. Log History (Audit)
        StatusHistory.objects.create(
            order_detail=item,
            old_status=old_status,
            new_status=new_status,
            changed_by=user
        )

        # 4. Notifications (Real-time)
        item_name = item.menu_item.name if item.menu_item else "Unknown Item"
        
        if new_status == StatusHistory.OrderStatus.READY:
            NotificationService.send_ready_signal(
                order_id=item.order.id, 
                item_name=item_name
            )
        
        elif new_status == StatusHistory.OrderStatus.CANCELLED:
            # Note: Reason handling should be passed in, simplified here
            NotificationService.send_cancellation_alert(
                order_id=item.order.id, 
                item_name=item_name,
                reason="Cancelled by Kitchen"
            )

        return item

    @staticmethod
    def get_pending_items():
        """
        Retrieve items needed for the KDS (Kitchen Display System).
        Filters for PENDING or COOKING items.
        """
        return OrderDetail.objects.filter(
            status__in=[
                StatusHistory.OrderStatus.PENDING, 
                StatusHistory.OrderStatus.COOKING
            ]
        ).select_related('menu_item', 'order', 'order__table').order_by('order__created_at')
