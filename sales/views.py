from typing import Any
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import RestaurantTable

class TableListView(LoginRequiredMixin, ListView):
    """
    Display a list of all restaurant tables.
    """
    model = RestaurantTable
    template_name = 'sales/table_list.html'
    context_object_name = 'tables'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Table Management'
        return context


class TableCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
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


class TableUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
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


class TableDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    Delete a restaurant table.
    """
    model = RestaurantTable
    template_name = 'sales/table_confirm_delete.html'
    success_url = reverse_lazy('sales:table_list')
    success_message = "Table was deleted successfully."

# --- POS Views ---

from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from menu.models import MenuItem, Category
from .models import Order, OrderDetail

@login_required
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
    categories = Category.objects.filter(is_active=True)
    
    # Get active category filter
    cat_id = request.GET.get('category')
    if cat_id:
        menu_items = MenuItem.objects.filter(category_id=cat_id, status='ACTIVE')
    else:
        menu_items = MenuItem.objects.filter(status='ACTIVE')

    # Get or create a PENDING order for this table
    # We do not create it yet, just try to fetch it. Creation happens on adding items.
    current_order = Order.objects.filter(
        table=table, 
        status=Order.Status.PENDING
    ).first()

    context = {
        'table': table,
        'categories': categories,
        'menu_items': menu_items,
        'current_order': current_order,
        'selected_cat': int(cat_id) if cat_id else None
    }
    return render(request, 'sales/pos_table_view.html', context)

@login_required
@require_POST
def add_to_cart(request: HttpRequest, table_id: int, item_id: int) -> HttpResponse:
    """
    HTMX View: Adds an item to the current Pending order for the table.
    Returns the updated Cart HTML partial.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    menu_item = get_object_or_404(MenuItem, pk=item_id)

    with transaction.atomic():
        # 1. Get or Create Order
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
        # Note: In a real POS, we might want separate lines for same item if modifiers differ.
        # For this base logic, we group by item.
        detail, detail_created = OrderDetail.objects.get_or_create(
            order=order,
            menu_item=menu_item,
            defaults={
                'quantity': 1,
                # unit_price is handled by save() method of OrderDetail
            }
        )

        if not detail_created:
            detail.quantity += 1
            detail.save()

        # 4. Recalculate Order Total (Handled by OrderDetail.save -> Order.update_total)
        # But we need to ensure the order object in context has the latest total
        order.refresh_from_db()

    # Return only the cart partial
    context = {'current_order': order, 'table': table}
    return render(request, 'sales/partials/cart_detail.html', context)

@login_required
@require_POST
def remove_from_cart(request: HttpRequest, table_id: int, detail_id: int) -> HttpResponse:
    """
    HTMX View: Removes an item (or decrements) from the order.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    order = get_object_or_404(Order, table=table, status=Order.Status.PENDING)
    detail = get_object_or_404(OrderDetail, pk=detail_id, order=order)

    with transaction.atomic():
        if detail.quantity > 1:
            detail.quantity -= 1
            detail.save()
        else:
            detail.delete()
            # Deletion should also trigger update_total, but Django signals/methods on delete 
            # might not unless we explicitly call it or use signals. 
            # Our model `update_total` is on Order. OrderDetail.save calls it.
            # OrderDetail.delete does NOT call save().
            # So we must manually update total.
            order.update_total()
        
        order.refresh_from_db()

    context = {'current_order': order, 'table': table}
    return render(request, 'sales/partials/cart_detail.html', context)

@login_required
@require_POST
def submit_order(request: HttpRequest, table_id: int) -> HttpResponse:
    """
    Finalizes the order: Changes status from Pending to Cooking.
    Redirects back to Table Map.
    """
    table = get_object_or_404(RestaurantTable, pk=table_id)
    order = get_object_or_404(Order, table=table, status=Order.Status.PENDING)

    if not order.details.exists():
        messages.error(request, "Cannot submit empty order.")
        return redirect('sales:pos_table_detail', table_id=table.table_id)

    # Change status to trigger Kitchen display
    order.status = Order.Status.COOKING
    order.save()
    
    messages.success(request, f"Order #{order.id} sent to Kitchen.")
    return redirect('sales:pos_index')


# --- Payment Views (Task 023) ---

from decimal import Decimal
from django.http import JsonResponse
from .services import PaymentController

@login_required
@require_POST
def process_payment(request: HttpRequest, order_id: int) -> JsonResponse:
    """
    API View to handle payment processing.
    Expects JSON or Form data:
    - amount: float
    - method: str (CASH, CARD, QR)
    """
    # Handle both JSON and Form data
    if request.content_type == 'application/json':
        import json
        data = json.loads(request.body)
        amount_val = data.get('amount')
        method = data.get('method', 'CASH')
    else:
        amount_val = request.POST.get('amount')
        method = request.POST.get('method', 'CASH')

    if not amount_val:
        return JsonResponse({'success': False, 'message': 'Amount is required'}, status=400)

    try:
        amount = Decimal(str(amount_val))
    except:
        return JsonResponse({'success': False, 'message': 'Invalid amount'}, status=400)

    result = PaymentController.process_payment(order_id, amount, method)
    
    status_code = 200 if result['success'] else 400
    return JsonResponse(result, status=status_code)
