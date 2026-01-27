from typing import Any, Dict
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, UpdateView, DetailView
from django.db import transaction
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import MenuItem, Pricing
from .forms import MenuItemForm, PricingForm

class MenuItemListView(LoginRequiredMixin, ListView):
    """
    UC1: List all menu items.
    Allows filtering by active/inactive via GET parameter 'view'.
    """
    model = MenuItem
    template_name = 'menu/menu_item_list.html'
    context_object_name = 'menu_items'
    paginate_by = 20

    def get_queryset(self):
        """
        Filter queryset based on view mode (active only vs all).
        """
        queryset = super().get_queryset().select_related('category')
        view_mode = self.request.GET.get('view', 'active')
        
        if view_mode == 'active':
            return queryset.filter(status='ACTIVE') # Uppercase matching choice
        elif view_mode == 'all':
            return queryset
        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['view_mode'] = self.request.GET.get('view', 'active')
        return context


@login_required
def menu_item_create_view(request: HttpRequest) -> HttpResponse:
    """
    UC1: Create a new Menu Item AND its initial Pricing.
    Uses function-based view to handle two forms easily within a transaction.
    """
    if request.method == 'POST':
        item_form = MenuItemForm(request.POST, request.FILES)
        price_form = PricingForm(request.POST)

        if item_form.is_valid() and price_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Save Menu Item (Populate 'price' field for compatibility/constraint)
                    menu_item = item_form.save(commit=False)
                    menu_item.price = price_form.cleaned_data['selling_price']
                    menu_item.save()

                    # 2. Save Pricing linked to Menu Item
                    pricing = price_form.save(commit=False)
                    pricing.menu_item = menu_item
                    # Convert Date to DateTime if needed, or let Django handle if field is DateTimeField
                    # Model effective_date is DateTimeField. Form is DateInput.
                    # It's safer to combine with min time if it's date only.
                    # But Django usually casts date to datetime at midnight.
                    pricing.save()

                messages.success(request, f"Menu Item '{menu_item.name}' created successfully.")
                return redirect('menu:menu_list')
            except Exception as e:
                # Transaction will auto-rollback here
                messages.error(request, f"Error saving data: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill effective date with today
        item_form = MenuItemForm()
        price_form = PricingForm(initial={'effective_date': timezone.now().date()})

    return render(request, 'menu/menu_item_form.html', {
        'item_form': item_form,
        'price_form': price_form,
        'title': 'Create Menu Item'
    })


class MenuItemUpdateView(LoginRequiredMixin, UpdateView):
    """
    UC1: Update Menu Item details (Name, Desc, Image, etc.).
    Note: Pricing is usually managed separately or via a specific history view,
    but we can allow editing the current item properties here.
    """
    model = MenuItem
    form_class = MenuItemForm
    template_name = 'menu/menu_item_edit.html'
    success_url = reverse_lazy('menu:menu_list')

    def form_valid(self, form):
        messages.success(self.request, "Menu item updated successfully.")
        return super().form_valid(form)


def menu_item_soft_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    UC1: Soft Delete / Deactivate Logic.
    Does NOT delete from DB. Sets status to 'Inactive'.
    """
    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    if request.method == 'POST':
        # Confirm soft delete
        menu_item.status = MenuItem.ItemStatus.INACTIVE
        menu_item.save()
        messages.warning(request, f"Item '{menu_item.name}' has been deactivated (Soft Delete).")
        return redirect('menu:menu_list')
    
    return render(request, 'menu/menu_item_confirm_delete.html', {'object': menu_item})
