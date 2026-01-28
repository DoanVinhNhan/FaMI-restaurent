import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from typing import Dict, Any

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer to handle real-time notifications for specific groups 
    (e.g., 'kitchen', 'cashier').
    """

    async def connect(self) -> None:
        """
        Called when the websocket is handshaking as part of the connection process.
        """
        # Get the group name from the URL route (defined in routing.py)
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        self.group_channel_name = f"notification_{self.group_name}"

        # Join the group
        await self.channel_layer.group_add(
            self.group_channel_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_channel_name,
            self.channel_name
        )

    async def receive_json(self, content: Dict[str, Any], **kwargs) -> None:
        pass

    async def broadcast_message(self, event: Dict[str, Any]) -> None:
        """
        Handler for messages sent to the group via channel_layer.group_send.
        The event dict contains the 'type' (this method name) and the 'payload'.
        """
        # Send message to WebSocket
        await self.send_json(event['payload'])
