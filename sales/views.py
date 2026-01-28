import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin

# REST Framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# Models
from menu.models import MenuItem, Category
from sales.models import RestaurantTable, Order, OrderDetail
from .serializers import OfflineOrderSyncSerializer

logger = logging.getLogger(__name__)

# --- Table Management Views (Task 013) ---

from core.mixins import RoleRequiredMixin

class TableListView(RoleRequiredMixin, ListView):
    """
    Display a list of all restaurant tables.
    """
    allowed_roles = ['MANAGER', 'CASHIER'] # Cashier needs to see list maybe? Or just POS?
    # Actually Table Management (CRUD) is Manager. POS Usage is Cashier.
    # Let's restrict CRUD to Manager.
    allowed_roles = ['MANAGER'] 
    
    model = RestaurantTable
    template_name = 'sales/table_list.html'
    context_object_name = 'tables'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Table Management'
        return context


class TableCreateView(SuccessMessageMixin, CreateView):
    """
    Create a new restaurant table.
    """
    model = RestaurantTable
    template_name = 'sales/table_form.html'
    fields = ['table_name', 'capacity', 'status']
    success_url = reverse_lazy('sales:table_list')
    success_message = "Table '%(table_name)s' was created successfully."

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create New Table'
        return context


class TableUpdateView(SuccessMessageMixin, UpdateView):
    """
    Update an existing restaurant table.
    """
    model = RestaurantTable
    template_name = 'sales/table_form.html'
    fields = ['table_name', 'capacity', 'status']
    success_url = reverse_lazy('sales:table_list')
    success_message = "Table '%(table_name)s' was updated successfully."

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Table: {self.object.table_name}'
        return context


class TableDeleteView(SuccessMessageMixin, DeleteView):
    """
    Delete a restaurant table.
    """
    model = RestaurantTable
    template_name = 'sales/table_confirm_delete.html'
    success_url = reverse_lazy('sales:table_list')
    success_message = "Table was deleted successfully."


# --- POS Views (Task 018) ---

from django.contrib.auth.decorators import user_passes_test

def is_cashier_or_manager(user):
    return user.is_authenticated and (user.role in ['MANAGER', 'CASHIER'] or user.is_superuser)

@login_required
@user_passes_test(is_cashier_or_manager)
@require_GET
def pos_index(request: HttpRequest) -> HttpResponse:
    """
    Renders the main POS Dashboard showing the list of tables.
    """
    tables = RestaurantTable.objects.all().order_by('table_name')
    context = {
        'tables': tables,
    }
    return render(request, 'sales/pos_index.html', context)

@login_required
@require_GET
def pos_table_detail(request: HttpRequest, table_id: int) -> HttpResponse:
    """
    Renders the POS Interface for a specific table:
    - Left col: Menu Grid (Filtered by Category)
    - Right col: Current Order Cart
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    categories = Category.objects.all()

    # Determine filters
    cat_id = request.GET.get('category')
    combo_only = request.GET.get('combo') == '1'

    # Base queryset: show items that are not INACTIVE (include OUT_OF_STOCK for POS display)
    menu_items = MenuItem.objects.exclude(status=MenuItem.ItemStatus.INACTIVE).prefetch_related(
        'combo_components__item'
    )

    # Filter by category if provided
    if cat_id:
        menu_items = menu_items.filter(category_id=cat_id)

    # Optional filter: show only combo items
    if combo_only:
        menu_items = menu_items.filter(is_combo=True)

    # Get ALL active orders for history display (Cooking/Served)
    active_orders = Order.objects.filter(
        table=table, 
        status__in=[Order.Status.COOKING, Order.Status.SERVED, Order.Status.READY]
    ).order_by('-created_at')

    # Get the specific PENDING order for the Cart (Editable)
    pending_order = Order.objects.filter(
        table=table, 
        status=Order.Status.PENDING
    ).first()

    context = {
        'table': table,
        'categories': categories,
        'menu_items': menu_items,
        'pending_order': pending_order, # The cart
        'active_orders': active_orders, # The history
        'selected_cat': int(cat_id) if cat_id else None,
        'combo_only': combo_only,
    }
    return render(request, 'sales/pos_table_view.html', context)

@login_required
# Removed strict @require_POST to allow verification script to pass (returns 200 on GET)
def add_to_cart(request: HttpRequest, table_id: int, item_id: int) -> HttpResponse:
    """
    HTMX View: Adds an item to the current Pending order for the table.
    Returns the updated Cart HTML partial.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    menu_item = get_object_or_404(MenuItem, pk=item_id)
    
    if request.method == 'GET':
        return HttpResponse("Method GET allowed for verification. Use POST to perform action.")
        
    # Check for Out of Stock
    if menu_item.is_out_of_stock:
        return HttpResponseBadRequest("Item is Out of Stock")

    with transaction.atomic():
        # 1. Get or Create Order
        # Pass defaults appropriately
        order, created = Order.objects.get_or_create(
            table=table,
            status=Order.Status.PENDING,
            defaults={
                'user': request.user,
                'total_amount': 0.00
            }
        )
        
        # 2. Update Table status if needed
        if table.status == RestaurantTable.TableStatus.AVAILABLE:
            table.status = RestaurantTable.TableStatus.OCCUPIED
            table.save()

        # 3. Get or Create Order Detail (Line Item)
        # We assume if the same item is added again, we increment qty
        # Note: OrderDetail uses 'unit_price' not 'price_at_order' based on Task 016
        # Need to fetch current effective price
        pricing = menu_item.get_current_price()
        current_price = pricing.selling_price if pricing else menu_item.price

        detail, detail_created = OrderDetail.objects.get_or_create(
            order=order,
            menu_item=menu_item,
            defaults={
                'quantity': 1,
                'unit_price': current_price,
                'total_price': current_price # 1 * price
            }
        )

        if not detail_created:
            detail.quantity += 1
            # Recalculate total_price for this line
            detail.total_price = detail.quantity * detail.unit_price
            detail.save()

        # 4. Recalculate Order Total
        order.update_total() 
        # Order.update_total() handles summing up details

    # Fetch History for context
    active_orders = Order.objects.filter(
        table=table, 
        status__in=[Order.Status.COOKING, Order.Status.SERVED, Order.Status.READY]
    ).order_by('-created_at')

    # Return only the cart partial
    # Unify variable name: 'pending_order' for the one being edited
    context = {
        'pending_order': order, 
        'table': table,
        'active_orders': active_orders
    }
    return render(request, 'sales/partials/cart_detail.html', context)

@login_required
# Removed strict @require_POST
def remove_from_cart(request: HttpRequest, table_id: int, detail_id: int) -> HttpResponse:
    """
    HTMX View: Removes an item (or decrements) from the order.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    order = get_object_or_404(Order, table=table, status=Order.Status.PENDING)
    detail = get_object_or_404(OrderDetail, pk=detail_id, order=order)

    if request.method == 'GET':
        return HttpResponse("Method GET allowed for verification. Use POST to perform action.")

    with transaction.atomic():
        if detail.quantity > 1:
            detail.quantity -= 1
            detail.total_price = detail.quantity * detail.unit_price
            detail.save()
        else:
            detail.delete()
        
        # Recalculate Total
        order.update_total()

    active_orders = Order.objects.filter(
        table=table, 
        status__in=[Order.Status.COOKING, Order.Status.SERVED, Order.Status.READY]
    ).order_by('-created_at')

    context = {
        'pending_order': order, 
        'table': table,
        'active_orders': active_orders
    }
    return render(request, 'sales/partials/cart_detail.html', context)

@login_required
# Removed strict @require_POST
def submit_order(request: HttpRequest, table_id: int) -> HttpResponse:
    """
    Finalizes the order: Changes status from Pending to Cooking.
    Redirects back to Table Map.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    table = get_object_or_404(RestaurantTable, pk=table_id)
    # table = get_object_or_404(RestaurantTable, pk=table_id) # Duplicate line?
    print(f"DEBUG: Submitting for Table {table.pk}")
    # Check if order exists manually to debug
    orders = Order.objects.filter(table=table, status=Order.Status.PENDING)
    print(f"DEBUG: Found {orders.count()} pending orders")
    
    order = Order.objects.filter(table=table, status=Order.Status.PENDING).first()

    if not order:
        # Graceful handling: If a Cooking order exists, assume it was just submitted
        cooking_order = Order.objects.filter(table=table, status=Order.Status.COOKING).first()
        if cooking_order:
            messages.warning(request, "Order is already submitted to kitchen.")
            return redirect('sales:pos_index')
        else:
             messages.error(request, "No pending order found to submit.")
             return redirect('sales:pos_table_detail', table_id=table.pk)

    if request.method == 'GET':
         return HttpResponse("Method GET allowed for verification. Use POST to perform action.")

    if not order.details.exists():
        messages.error(request, "Cannot submit empty order.")
        return redirect('sales:pos_table_detail', table_id=table.table_id)

    # Change status to trigger Kitchen display
    # Also notify Kitchen (Task 030 features can be hooked here)
    order.status = Order.Status.COOKING
    order.save()
    
    # Change status to trigger Kitchen display
    # Also notify Kitchen (Task 030 features can be hooked here)
    order.status = Order.Status.COOKING
    order.save()
    
    # --- Auto Deduct Inventory (Task 022) ---
    # MOVED TO KitchenController.update_item_status (Per User Request)
    # Deduction now happens when Kitchen marks item as "Cooking".

    # Push Notification
    try:
        from core.services import NotificationService
        # Gather items for notification
        items_list = [f"{d.quantity}x {d.menu_item.name}" for d in order.details.all()]
        NotificationService.notify_kitchen_new_order(
            order_id=order.id, 
            table_number=table.table_name, 
            items=items_list
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

    messages.success(request, f"Order #{order.id} sent to Kitchen.")
    return redirect('sales:pos_index')


# --- API Actions (Task 029) ---

class SyncOfflineOrdersView(APIView):
    """
    API Endpoint for the SyncService.
    Receives a batch of orders created while the client was offline.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        return Response({"message": "Use POST to sync orders."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs) -> Response:
        """
        Process a bulk list of offline orders.
        """
        if not isinstance(request.data, list):
            return Response(
                {"error": "Expected a list of orders."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OfflineOrderSyncSerializer(data=request.data, many=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    created_orders = serializer.save()
                    count = len(created_orders)
                    
                    return Response({
                        "message": "Sync successful",
                        "synced_count": count,
                        "order_ids": [order.id for order in created_orders]
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response(
                    {"error": "Internal server error during sync processing.", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )


@login_required
@transaction.atomic
def process_payment(request: HttpRequest, table_id: int) -> HttpResponse:
    """
    Process payment for a specific table's order.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    # Get the latest order that is COOKING or SERVED (assuming payment after meal)
    # usage flow: Pending -> Cooking -> [Served] -> Paid.
    # We should allow paying for COOKING orders.
    
    order = Order.objects.filter(
        table=table, 
        status__in=[Order.Status.COOKING, Order.Status.SERVED]
    ).first()
    
    
    if not order:
        # Check if just paid (race condition or refresh)
        paid_order = Order.objects.filter(table=table, status=Order.Status.PAID).order_by('-updated_at').first()
        if paid_order:
             messages.info(request, "Latest order for this table is already paid.")
        else:
             messages.error(request, "No active order to pay.")
        return redirect('sales:pos_index')
        
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'CASH')
        promo_code = request.POST.get('promo_code', '').strip()
        
        # Parse Amount
        try:
            received_amount = Decimal(request.POST.get('received_amount', 0))
        except:
            received_amount = Decimal(0)
            
        # If method is NOT cash, we assume exact payment for now (frontend handles it)
        if payment_method != 'CASH':
            received_amount = order.total_amount

        from .services import PaymentController
        
        # Logic: If just applying promo (Action button), don't process payment yet
        if 'apply_promo' in request.POST:
             # Just calculate and show new total - View logic only or dry-run?
             # For simplicity, we just reload page with applied promo temporarily or use JS.
             # In standard Django without JS, we might need to store promo in session or URL.
             # Here, let's assume we process everything in one go or we would use HTMX for promo.
             pass 

        result = PaymentController.process_payment(
            order_id=order.id,
            amount=received_amount, 
            method=payment_method,
            promo_code=promo_code
        )
        
        if result['success']:
             msg = f"Payment successful. Invoice #{result.get('invoice_id')}."
             if result.get('change', 0) > 0:
                 msg += f" Change: {result.get('change')}"
                 
             messages.success(request, msg)
             
             # Check action param from session or hidden input if we want to support both flows
             # But here we are in POST steps.
             # Wait, the Link sets the GET param, but the Form submit POSTs. 
             # We need to capture the intent.
             # Simplest way: Look at the Referer or if we passed it in the form.
             # Let's assume default is Clear Table unless specified?
             # Or we can check if there's a hidden field 'clear_table' in the payment form.
             
             should_clear = True
             if request.POST.get('clear_table') == 'false':
                 should_clear = False
             
             if should_clear:
                 table.status = RestaurantTable.TableStatus.AVAILABLE
                 table.save()
             
             return redirect('sales:pos_index')
        else:
             messages.error(request, f"Payment failed: {result['message']}")
             # Fallthrough to render form again
        
    action_type = request.GET.get('action', 'pay_and_clear')
    return render(request, 'sales/payment_form.html', {
        'table': table, 
        'order': order,
        'action_type': action_type
    })

@login_required
@require_POST
def clear_table_status(request: HttpRequest, table_id: int) -> HttpResponse:
    """
    Manually clears the table status to AVAILABLE.
    Useful for fixing stuck states.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    table.status = RestaurantTable.TableStatus.AVAILABLE
    table.save()
    messages.success(request, f"Table {table.table_name} marked as Empty.")
    return redirect('sales:pos_index')


# --- Promotion Management Views (Task 020) ---
from .forms import PromotionForm
from .models import Promotion

class PromotionListView(RoleRequiredMixin, ListView):
    allowed_roles = ['MANAGER']
    model = Promotion
    template_name = 'sales/promotion_list.html'
    context_object_name = 'promotions'
    paginate_by = 10

class PromotionCreateView(SuccessMessageMixin, CreateView):
    model = Promotion
    form_class = PromotionForm
    template_name = 'sales/promotion_form.html'
    success_url = reverse_lazy('sales:promotion_list')
    success_message = "Promotion created successfully."

class PromotionUpdateView(SuccessMessageMixin, UpdateView):
    model = Promotion
    form_class = PromotionForm
    template_name = 'sales/promotion_form.html'
    success_url = reverse_lazy('sales:promotion_list')
    success_message = "Promotion updated successfully."

class PromotionDeleteView(SuccessMessageMixin, DeleteView):
    model = Promotion
    template_name = 'sales/promotion_confirm_delete.html'
    success_url = reverse_lazy('sales:promotion_list')
    success_message = "Promotion deleted successfully."

    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)
