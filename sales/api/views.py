from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from django.shortcuts import get_object_or_404
from sales.models import Order, OrderDetail, RestaurantTable
from menu.models import MenuItem
from django.contrib.auth import get_user_model
from core.services import NotificationService
from inventory.services import InventoryService
from decimal import Decimal

User = get_user_model()

class CreateThirdPartyOrderView(APIView):
    """
    API for 3rd Party services (Grab/Shopee) to push orders.
    Spec: Create_Order/sequence.puml
    """
    permission_classes = [permissions.AllowAny] # Open for 3rd party integration via signature validation later

    def post(self, request):
        data = request.data
        
        # 1. Validation (Fail-Fast)
        partner_ref = data.get('partner_order_id')
        items = data.get('items', [])
        
        if not partner_ref or not items:
            return Response({"error": "Missing partner_order_id or items"}, status=status.HTTP_400_BAD_REQUEST)

        # Idempotency Check
        if Order.objects.filter(external_id=partner_ref).exists():
             return Response({"message": "Order already exists"}, status=status.HTTP_200_OK)

        # 2. Check Restaurant Status
        from core.services import RestaurantService
        if not RestaurantService.is_open():
            return Response(
                {"error": "Restaurant is currently closed."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        unavailable_items = []
        
        try:
            with transaction.atomic():
                # 3. Create Order Header (Placeholder)
                # Assign to a specific "Delivery" table or virtual table
                system_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if not system_user:
                     raise Exception("No system user available to assign order")
                
                order = Order.objects.create(
                    external_id=partner_ref,
                    user=system_user,
                    status=Order.Status.PENDING,
                    total_amount=0
                )
                
                total_amount = Decimal(0)
                is_manual_review_needed = False
                price_mismatch_warning = None
                
                # 4. Process Items and Validate Stock
                created_details = []
                
                for item_data in items:
                    sku = item_data.get('sku')
                    qty = item_data.get('quantity', 1)
                    incoming_price = Decimal(str(item_data.get('price', 0))) # Partner sent price
                    
                    try:
                        # Lookup by SKU field as per API contract. 
                        # Fallback to ID if SKU not found or implemented as ID
                        menu_item = MenuItem.objects.get(sku=sku) 
                    except MenuItem.DoesNotExist:
                         return Response({"error": f"Invalid Menu Item SKU: {sku}"}, status=status.HTTP_400_BAD_REQUEST)

                    if menu_item.is_out_of_stock:
                         unavailable_items.append({sku: "Out of Stock"})
                         continue

                    if not menu_item.is_active:
                         unavailable_items.append({sku: "Item is inactive"})
                         continue

                    # Inventory Check
                    is_available = InventoryService.check_availability(menu_item, qty)
                    if not is_available:
                        unavailable_items.append({sku: "Out of Stock"})
                        continue

                    # Price Check (5% Tolerance)
                    if incoming_price > 0:
                        db_price = menu_item.price
                        diff = abs(incoming_price - db_price)
                        max_diff = db_price * Decimal('0.05')
                        
                        if diff > max_diff:
                            is_manual_review_needed = True
                            price_mismatch_warning = "Price mismatch detected. Manual confirmation required."
                    
                    line_total = menu_item.price * qty
                    total_amount += line_total
                    
                    detail = OrderDetail.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=qty,
                        unit_price=menu_item.price,
                        total_price=line_total,
                        status=Order.Status.PENDING
                    )
                    created_details.append(detail)

                # 5. Handle Stock Failures (Luồng thay thế - Out of Stock)
                if unavailable_items:
                    # Rollback transaction manually implied by exception or allow atomic to handle?
                    # Since we are inside atomic block, raising exception rolls back.
                    raise RuntimeError("Stock Unavailable") 

                # 6. Finalize Order
                order.total_amount = total_amount
                
                # Decision for Status
                if not is_manual_review_needed:
                    order.status = Order.Status.COOKING
                    order.save()
                    
                    # Notify Kitchen (Async)
                    items_str = [f"{d.quantity}x {d.menu_item.name}" for d in created_details]
                    NotificationService.notify_kitchen_new_order(
                        order_id=order.id,
                        table_number="DELIVERY",
                        items=items_str
                    )
                else:
                    order.status = Order.Status.PENDING
                    order.save()
                    # Notify Cashier about Mismatch (Task for Cashier Alert)
                    # For now just log or basic signal

                response_data = {
                    "success": True, 
                    "internal_order_id": order.id,
                    "status": order.status
                }
                
                if price_mismatch_warning:
                    response_data["warning"] = price_mismatch_warning

                return Response(response_data, status=status.HTTP_201_CREATED)

        except RuntimeError as e:
            if "Stock Unavailable" in str(e):
                return Response(
                    {
                        "error": "One or more items are unavailable",
                        "unavailable_items": unavailable_items
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
