from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import InventoryItem, StockTakeTicket, StockTakeDetail, Ingredient, InventoryLog
from .forms import StockTakeTicketForm, StockTakeDetailFormSet

# --- Task 009: Ingredient Views ---

from core.mixins import RoleRequiredMixin

class IngredientListView(RoleRequiredMixin, ListView):
    allowed_roles = ['MANAGER', 'INVENTORY']
    model = Ingredient
    template_name = 'inventory/ingredient_list.html'
    context_object_name = 'ingredients'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            from django.db.models import Q
            queryset = queryset.filter(Q(name__icontains=query) | Q(sku__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class IngredientCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['MANAGER', 'INVENTORY']
    model = Ingredient
    template_name = 'inventory/ingredient_form.html'
    fields = ['sku', 'name', 'unit', 'cost_per_unit', 'alert_threshold']
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, "Ingredient created successfully.")
        return super().form_valid(form)

class IngredientUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['MANAGER', 'INVENTORY']
    model = Ingredient
    template_name = 'inventory/ingredient_form.html'
    fields = ['sku', 'name', 'unit', 'cost_per_unit', 'alert_threshold']
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, "Ingredient updated successfully.")
        return super().form_valid(form)

class IngredientDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = ['MANAGER', 'INVENTORY']
    model = Ingredient
    template_name = 'inventory/ingredient_confirm_delete.html'
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Dependency Checks
        # 1. Check if used in any Recipe
        if self.object.used_in_recipes.exists():
            messages.error(self.request, "Cannot delete ingredient because it is used in one or more recipes.")
            return redirect('inventory:ingredient_list')

        # 2. Check if Stock > 0
        try:
             # Refresh from DB to ensure we have latest relation
             # Use related_name 'inventory_stock' (OneToOne)
             if hasattr(self.object, 'inventory_stock') and self.object.inventory_stock.quantity_on_hand > 0:
                 messages.error(self.request, f"Cannot delete ingredient. Stock on hand is {self.object.inventory_stock.quantity_on_hand} {self.object.unit}.")
                 return redirect('inventory:ingredient_list')
        except Exception as e:
             pass

        try:
            self.object.delete()
            messages.success(self.request, "Ingredient deleted successfully.")
            return redirect(success_url)
        except Exception as e:
            # Catch ProtectedError here if manual check missed something
            messages.error(self.request, "Cannot delete ingredient due to dependencies.")
            return redirect('inventory:ingredient_list')

# --- Task 008: Inventory Management Views ---

from django.contrib.auth.decorators import user_passes_test

def is_inventory_manager(user):
    return user.is_authenticated and (user.role in ['MANAGER', 'INVENTORY'] or user.is_superuser)

@login_required
@user_passes_test(is_inventory_manager)
def inventory_dashboard(request):
    """
    Overview of current stock levels and alerts.
    """
    items = InventoryItem.objects.select_related('ingredient').all()
    # Logic to filter low stock could be here or in template
    low_stock_items = [item for item in items if item.is_low_stock()]
    
    context = {
        'total_items': items.count(),
        'low_stock_count': len(low_stock_items),
        'inventory_items': items,
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def adjust_stock(request, pk):
    """
    Manually adjust stock level for an item.
    """
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        try:
            new_qty = float(request.POST.get('quantity'))
            reason = request.POST.get('reason')
            
            # Create Log
            InventoryLog.objects.create(
                ingredient=item.ingredient,
                user=request.user,
                change_type='ADJUSTMENT',
                quantity_change=new_qty - float(item.quantity_on_hand),
                reason=reason
            )
            
            # Update Item
            item.quantity_on_hand = new_qty
            item.save()
            messages.success(request, f"Stock updated for {item.ingredient.name}")
            return redirect('inventory:dashboard')
        except ValueError:
            messages.error(request, "Invalid quantity")
            
    return render(request, 'inventory/adjust_stock.html', {'item': item})

@login_required
def inventory_logs(request):
    logs = InventoryLog.objects.select_related('ingredient', 'user').order_by('-created_at')[:50]
    return render(request, 'inventory/logs.html', {'logs': logs})

# --- Task 025: Stock Take Views ---

@login_required
@user_passes_test(is_inventory_manager)
def stock_take_list(request):
    """
    List all stock take history.
    """
    tickets = StockTakeTicket.objects.select_related('creator').all().order_by('-created_at')
    return render(request, 'inventory/stocktake_list.html', {'tickets': tickets})

@login_required
@transaction.atomic
def stock_take_create(request):
    """
    Initialize a new Stock Take session.
    Logic: SNAPSHOT all current inventory items immediately.
    """
    if request.method == 'POST':
        form = StockTakeTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            ticket.status = StockTakeTicket.Status.DRAFT
            # Generate a code if not provided (simple logic for now)
            # ideally this should be auto-generated in model or service
            import datetime
            count = StockTakeTicket.objects.count() + 1
            ticket.code = f"ST-{datetime.date.today().strftime('%Y%m%d')}-{count:03d}"
            ticket.save()

            # Snapshot Logic
            inventory_items = InventoryItem.objects.select_related('ingredient').all()
            details = []
            for item in inventory_items:
                details.append(StockTakeDetail(
                    ticket=ticket,
                    ingredient=item.ingredient, # Link to Ingredient
                    snapshot_quantity=item.quantity_on_hand,
                    actual_quantity=item.quantity_on_hand # Default to current to avoid massive variance if untouched
                ))
            
            # Bulk create for performance
            StockTakeDetail.objects.bulk_create(details)
            
            messages.success(request, f"Stock Take {ticket.code} started. Inventory snapshot taken.")
            return redirect('inventory:stock_take_detail', ticket_id=ticket.ticket_id)
    else:
        form = StockTakeTicketForm()
    
    return render(request, 'inventory/stocktake_create.html', {'form': form})

@login_required
def stock_take_detail(request, ticket_id):
    """
    View to input actual counts.
    Handles 'Save Draft' and 'Finalize'.
    """
    ticket = get_object_or_404(StockTakeTicket, pk=ticket_id)
    
    # Prevent editing if already finalized
    if ticket.status != StockTakeTicket.Status.DRAFT:
        details = ticket.details.select_related('ingredient').all()
        return render(request, 'inventory/stocktake_readonly.html', {
            'ticket': ticket, 
            'details': details
        })

    # Filter details for this ticket
    queryset = StockTakeDetail.objects.filter(ticket=ticket).select_related('ingredient')

    if request.method == 'POST':
        formset = StockTakeDetailFormSet(request.POST, queryset=queryset)
        
        if formset.is_valid():
            # Save Draft Logic
            formset.save()
            
            # Check if User clicked "Finalize" button
            if 'finalize' in request.POST:
                return finalize_stock_take(request, ticket)
            
            messages.success(request, "Counts saved as draft.")
            return redirect('inventory:stock_take_detail', ticket_id=ticket.ticket_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        formset = StockTakeDetailFormSet(queryset=queryset)

    return render(request, 'inventory/stocktake_form.html', {
        'ticket': ticket,
        'formset': formset
    })

@transaction.atomic
def finalize_stock_take(request, ticket):
    """
    Apply variances to live inventory and close ticket.
    """
    # Refetch details to ensure we have latest DB state
    details = ticket.details.select_related('ingredient').all()
    
    total_variance_value = 0
    
    for detail in details:
        # Calculate Variance
        # Note: logic inside StockTakeDetail.save() calculates the variance field, 
        # but we need to update the variance field explicitly if we saved via formset?
        # Formset save() calls model save(), so variance refers to (actual - snapshot).
        # We assume actual_quantity is set.
        
        # Update Live Inventory
        # We need to find the InventoryItem corresponding to the Ingredient
        try:
             # Use select_for_update or get to lock row
             inv_item = InventoryItem.objects.select_for_update().get(ingredient=detail.ingredient)
             
             # Requirement: "Adjust Inventory upon finalization" -> Set to Actual.
             if detail.actual_quantity is not None:
                 inv_item.quantity_on_hand = detail.actual_quantity
                 inv_item.save()
                 
                 # Recalculate cost impact
                 cost = detail.ingredient.cost_per_unit
                 total_variance_value += (detail.variance * cost)
                 
        except InventoryItem.DoesNotExist:
             # Should not happen if snapshot was correct, but maybe item deleted?
             pass

    # Update Ticket Header
    ticket.status = StockTakeTicket.Status.COMPLETED
    ticket.variance_total_value = total_variance_value
    ticket.save()

    messages.success(request, "Stock Take Finalized. Inventory updated.")
    return redirect('inventory:stock_take_list')
