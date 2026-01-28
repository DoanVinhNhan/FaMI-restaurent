from rest_framework import serializers
from django.db import transaction
from .models import RestaurantTable, Order, OrderDetail
from menu.models import MenuItem

class RestaurantTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = ['table_id', 'table_name', 'capacity', 'status']

class OrderDetailSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    total_line_price = serializers.DecimalField(source='total_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderDetail
        fields = [
            'id', 'menu_item', 'menu_item_name', 'quantity', 
            'unit_price', 'note', 'total_price', 'total_line_price', 'status'
        ]
        read_only_fields = ['unit_price', 'total_price', 'status']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderDetailSerializer(source='details', many=True, read_only=True)
    items_payload = serializers.ListField(
        child=serializers.DictField(), 
        write_only=True,
        required=True
    )
    table_name = serializers.CharField(source='table.table_name', read_only=True)
    created_by_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'external_id', 'table', 'table_name', 'status', 'total_amount', 
            'created_at', 'created_by_username', 'items', 'items_payload'
        ]
        read_only_fields = ['total_amount', 'created_at', 'status', 'created_by_username']

    def create(self, validated_data):
        items_data = validated_data.pop('items_payload')
        user = self.context['request'].user
        
        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)
            
            for item_data in items_data:
                menu_item_id = item_data.get('menu_item_id')
                quantity = item_data.get('quantity', 1)
                note = item_data.get('note', '')

                try:
                    menu_item = MenuItem.objects.get(id=menu_item_id)
                except MenuItem.DoesNotExist:
                     raise serializers.ValidationError(f"MenuItem with id {menu_item_id} does not exist")
                
                # Calculate price at moment of order
                # Ideally OrderDetail manager or save method handles this logic, 
                # but explicit setting here ensures we control exactly what goes in.
                pricing = menu_item.get_current_price()
                unit_price = pricing.selling_price if pricing else menu_item.price
                total_price = unit_price * quantity
                
                OrderDetail.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    note=note,
                    unit_price=unit_price,
                    total_price=total_price
                )

            # Update total
            order.update_total()
            
            return order

class OrderDetailSyncSerializer(serializers.ModelSerializer):
    """
    Serializer for processing individual items within an offline order.
    """
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(),
        source='menu_item',
        write_only=True
    )
    # Receive price snapshot from client to respect offline pricing
    price_snapshot = serializers.DecimalField(source='unit_price', max_digits=10, decimal_places=2)

    class Meta:
        model = OrderDetail
        fields = ['item_id', 'quantity', 'price_snapshot', 'note']

class OfflineOrderSyncSerializer(serializers.ModelSerializer):
    """
    Serializer for receiving a complete order structure from offline clients.
    """
    items = OrderDetailSyncSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'table', 'user', 'total_amount', 'status', 
            'created_at', 'items'
        ]
        extra_kwargs = {
            'created_at': {'required': True},
            'status': {'required': False}
        }

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Create the parent Order
        order = Order.objects.create(**validated_data)

        # Create child OrderDetails
        details_to_create = []
        for item_data in items_data:
            # item_data has 'menu_item' from source='menu_item' in OrderDetailSyncSerializer
            # and 'unit_price' from source='unit_price'
            
            # Calculate total for line
            qty = item_data.get('quantity', 1)
            unit_price = item_data.get('unit_price')
            
            details_to_create.append(
                OrderDetail(
                    order=order,
                    menu_item=item_data['menu_item'],
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=unit_price * qty,
                    note=item_data.get('note', '')
                )
            )
        
        OrderDetail.objects.bulk_create(details_to_create)

        return order
