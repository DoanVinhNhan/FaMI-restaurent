import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service responsible for handling real-time notifications via WebSocket 
    (Django Channels) or other mechanisms.
    
    Current implementation logs to console (Mock) but is structured for 
    Channels integration.
    """

    @staticmethod
    def send_ready_signal(order_id: int, item_name: str) -> None:
        """
        Notify Cashier/Waiter that an item is ready to be served.
        
        Args:
            order_id (int): The ID of the order.
            item_name (str): The name of the completed item.
        """
        # TODO: Replace with channel_layer.group_send for Django Channels
        payload: Dict[str, Any] = {
            "type": "order.ready",
            "order_id": order_id,
            "message": f"Item '{item_name}' for Order #{order_id} is READY."
        }
        logger.info(f"Broadcast to Cashier: {payload}")
        print(f"--> [WEBSOCKET MOCK] Sending 'Ready' signal to Cashiers: {payload}")

    @staticmethod
    def send_cancellation_alert(order_id: int, item_name: str, reason: str) -> None:
        """
        Notify Cashier that an item was cancelled by the kitchen.
        
        Args:
            order_id (int): The ID of the order.
            item_name (str): The name of the item.
            reason (str): The reason for cancellation.
        """
        payload: Dict[str, Any] = {
            "type": "order.cancelled",
            "order_id": order_id,
            "message": f"Item '{item_name}' CANCELLED. Reason: {reason}"
        }
        logger.warning(f"Broadcast to Cashier: {payload}")
        print(f"--> [WEBSOCKET MOCK] Sending 'Cancel' alert to Cashiers: {payload}")

    @staticmethod
    def notify_kitchen_new_ticket(order_id: int) -> None:
        """
        Notify Kitchen screens that a new ticket has arrived.
        """
        payload: Dict[str, Any] = {
            "type": "kitchen.new_ticket",
            "order_id": order_id
        }
        logger.info(f"Broadcast to Kitchen: {payload}")
        print(f"--> [WEBSOCKET MOCK] New Ticket Alert for Kitchen: {payload}")
