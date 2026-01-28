from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from typing import Dict, Any
from .models import SystemSetting

class RestaurantService:
    """
    Service to handle restaurant-wide logic.
    """
    @staticmethod
    def is_open() -> bool:
        """
        Checks if the restaurant is currently open.
        Defaults to True if setting is missing.
        """
        try:
            setting = SystemSetting.objects.get(setting_key='RESTAURANT_STATUS')
            # Assuming value 'OPEN' or 'CLOSED'
            return setting.setting_value.upper() == 'OPEN'
        except SystemSetting.DoesNotExist:
            # Default to Open if not configured
            return True

class NotificationService:
    """
    Service to broadcast messages to WebSocket groups from synchronous code.
    """

    @staticmethod
    def send_to_group(group_name: str, message_type: str, data: Dict[str, Any]) -> None:
        """
        Sends a message to a specific WebSocket group.

        Args:
            group_name (str): The target group (e.g., 'kitchen', 'cashier').
            message_type (str): The type of event (e.g., 'NEW_ORDER', 'ORDER_READY').
            data (dict): The payload data.
        """
        channel_layer = get_channel_layer()
        
        payload = {
            "type": message_type,
            "data": data,
            # "timestamp": timezone.now().isoformat() 
        }

        # The 'type' key in the group_send dictionary corresponds to the 
        # method name in the Consumer. We defined 'broadcast_message' in consumers.py.
        async_to_sync(channel_layer.group_send)(
            f"notification_{group_name}",
            {
                "type": "broadcast_message",
                "payload": payload
            }
        )

    @staticmethod
    def notify_kitchen_new_order(order_id: int, table_number: str, items: list) -> None:
        """
        Helper: Notify Kitchen about a new order.
        """
        NotificationService.send_to_group(
            group_name='kitchen',
            message_type='NEW_ORDER',
            data={
                "order_id": order_id,
                "table": table_number,
                "items": items
            }
        )

    @staticmethod
    def send_ready_signal(order_id: int, item_name: str) -> None:
        """
        Notify that an item is Ready (Done).
        """
        NotificationService.send_to_group(
            group_name='cashier',
            message_type='ORDER_READY',
            data={
                "order_id": order_id,
                "item_name": item_name
            }
        )

    @staticmethod
    def send_cancellation_alert(order_id: int, item_name: str, reason: str) -> None:
        """
        Notify that an item was cancelled.
        """
        NotificationService.send_to_group(
            group_name='cashier',
            message_type='ORDER_CANCELLED',
            data={
                "order_id": order_id,
                "item_name": item_name,
                "reason": reason
            }
        )
