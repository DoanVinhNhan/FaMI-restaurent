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
    Spec: Create_Order.tex
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

        try:
            with transaction.atomic():
                # 2. Create Order Header
                # Assign to a specific "Delivery" table or virtual table
                # For now, finding an available table or using a reserved ID
                # Simplification: Create without Table for Delivery, or assign Table 999
                # We need a user to attribute to.
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
                
                # 3. Process Items
                created_details = []
                for item_data in items:
                    sku = item_data.get('sku')
                    qty = item_data.get('quantity', 1)
                    incoming_price = Decimal(str(item_data.get('price', 0))) # Partner sent price
                    
                    # Inventory Check (Optimistic)
                    # We assume SKU exists or lookup by ID would work if SKU field exists 
                    # Note: schema might not have SKU on MenuItem, checking models...
                    # If MenuItem doesn't have SKU, we assume ID or code. 
                    # Let's assume passed sku matches 'id' or we need to filter.
                    # Ideally MenuItem has a code.
                    
                    try:
                        # Lookup by SKU field as per API contract
                        menu_item = MenuItem.objects.get(sku=sku) 
                    except MenuItem.DoesNotExist:
                         raise Exception(f"Invalid Menu Item SKU: {sku}")


                    if menu_item.status != 'ACTIVE':
                         raise Exception(f"Item {menu_item.name} is not active")

                    # Inventory Check
                    is_available = InventoryService.check_availability(menu_item, qty)
                    if not is_available:
                        # Requirement: "Hết hàng" -> Từ chối tạo đơn
                        raise Exception(f"Item {menu_item.name} is Out of Stock")

                    # Price Check (5% Tolerance)
                    # If incoming_price is provided, check it.
                    if incoming_price > 0:
                        db_price = menu_item.price
                        diff = abs(incoming_price - db_price)
                        max_diff = db_price * Decimal('0.05')
                        
                        if diff > max_diff:
                            # Requirement: "Ghi nhận cảnh báo, đánh dấu 'Xác nhận thủ công'"
                            is_manual_review_needed = True
                    
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

                # 4. Finalize
                order.total_amount = total_amount
                
                # If Status wasn't forced to PENDING by price check, set to COOKING (Auto-Accept)
                if not is_manual_review_needed and all(item.get('price', 0) for item in items):
                     # Simple logic: If we didn't hit price mismatch, auto-fire
                     order.status = Order.Status.COOKING
                else:
                     order.status = Order.Status.PENDING
                
                order.save()
                
                # 5. Notify Kitchen
                items_str = [f"{d.quantity}x {d.menu_item.name}" for d in created_details]
                NotificationService.notify_kitchen_new_order(
                    order_id=order.id,
                    table_number="DELIVERY",
                    items=items_str
                )

                return Response({
                    "success": True, 
                    "order_id": order.id,
                    "status": order.status
                }, status=status.HTTP_201_CREATED)

        except MenuItem.DoesNotExist:
             return Response({"error": "Invalid Menu Item SKU"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
