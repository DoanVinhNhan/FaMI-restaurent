from rest_framework import serializers
from sales.models import OrderDetail
from kitchen.models import StatusHistory

class KitchenItemStatusSerializer(serializers.Serializer):
    """
    Input serializer for status update requests.
    """
    status = serializers.ChoiceField(choices=StatusHistory.OrderStatus.choices)

class OrderDetailKitchenSerializer(serializers.ModelSerializer):
    """
    Output serializer for KDS display.
    """
    item_name = serializers.CharField(source='menu_item.name', read_only=True)
    table_id = serializers.CharField(source='order.table.table_name', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    notes = serializers.CharField(source='note', read_only=True)

    class Meta:
        model = OrderDetail
        fields = [
            'id', 
            'order_id', 
            'table_id', 
            'item_name', 
            'quantity', 
            'status', 
            'notes'
        ]
