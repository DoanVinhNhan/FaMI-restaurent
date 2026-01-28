from typing import Any, Dict
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, UpdateView, DetailView
from django.db import transaction
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import MenuItem, Pricing
from .forms import MenuItemForm, PricingForm

from core.mixins import RoleRequiredMixin
from django.contrib.auth.decorators import user_passes_test

def is_manager(user):
    return user.is_authenticated and (user.is_manager() or user.is_superuser)

class MenuItemListView(RoleRequiredMixin, ListView):
    """
    UC1: List all menu items.
    Allows filtering by active/inactive via GET parameter 'view'.
    """
    allowed_roles = ['MANAGER']
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
@user_passes_test(is_manager)
def menu_item_create_view(request: HttpRequest) -> HttpResponse:
    """
    UC1: Create a new Menu Item AND its initial Pricing.
    Uses function-based view to handle two forms easily within a transaction.
    """
    if request.method == 'POST':
        print(f"DEBUG: Processing Order POST. User: {request.user}")
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


@login_required
@user_passes_test(is_manager)
def menu_item_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    UC1: Update Menu Item details.
    Logic:
    - Load Item and Current Pricing.
    - If Price is changed -> Create NEW Pricing record (History).
    - Update MenuItem fields.
    """
    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    # Get current active pricing to pre-fill
    current_pricing = menu_item.get_current_price()
    initial_price = current_pricing.selling_price if current_pricing else menu_item.price
    
    if request.method == 'POST':
        item_form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        # We use PricingForm but don't bind it to an instance because we want to CREATE a new one if changed
        # Or we bind to a dummy to validate.
        price_form = PricingForm(request.POST)

        if item_form.is_valid() and price_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Update MenuItem
                    saved_item = item_form.save(commit=False)
                    new_price = price_form.cleaned_data['selling_price']
                    
                    # Check if price changed
                    # Logic: If price different from initial, create new record
                    if new_price != initial_price:
                        # Create new Pricing
                        Pricing.objects.create(
                            menu_item=saved_item,
                            selling_price=new_price,
                            effective_date=timezone.now() # Immediate effect
                        )
                        # Update display price on item
                        saved_item.price = new_price
                    
                    saved_item.save()
                    
                messages.success(request, f"Menu Item '{menu_item.name}' updated successfully.")
                return redirect('menu:menu_list')
            except Exception as e:
                messages.error(request, f"Error updating item: {e}")
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        item_form = MenuItemForm(instance=menu_item)
        price_form = PricingForm(initial={'selling_price': initial_price, 'effective_date': timezone.now()})

    return render(request, 'menu/menu_item_edit.html', {
        'item_form': item_form,
        'price_form': price_form,
        'object': menu_item,
        'title': f'Edit {menu_item.name}'
    })


@login_required
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

# --- Recipe Management Views (UC: Manage Recipes) ---
from .models import Recipe, RecipeIngredient
from .forms import RecipeForm, RecipeIngredientForm

@login_required
@user_passes_test(is_manager)
def menu_recipe_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Manage Recipe for a specific MenuItem.
    Handles:
    - Updating instructions.
    - Adding ingredients.
    - Removing ingredients.
    """
    menu_item = get_object_or_404(MenuItem, pk=pk)
    
    # Get or Create Recipe
    recipe, created = Recipe.objects.get_or_create(menu_item=menu_item)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_instructions':
            recipe_form = RecipeForm(request.POST, instance=recipe)
            if recipe_form.is_valid():
                recipe_form.save()
                messages.success(request, "Recipe instructions updated.")
            else:
                messages.error(request, "Error updating instructions.")
                
        elif action == 'add_ingredient':
            ing_form = RecipeIngredientForm(request.POST)
            if ing_form.is_valid():
                # Check duplicate
                ingredient = ing_form.cleaned_data['ingredient']
                if RecipeIngredient.objects.filter(recipe=recipe, ingredient=ingredient).exists():
                     messages.warning(request, f"Ingredient '{ingredient.name}' is already in the recipe.")
                else:
                    new_ing = ing_form.save(commit=False)
                    new_ing.recipe = recipe
                    new_ing.save()
                    messages.success(request, f"Added '{ingredient.name}' to recipe.")
                    return redirect('menu:recipe_manage', pk=pk) # Redirect to clear form
            else:
                messages.error(request, "Invalid ingredient data.")
                
        elif action == 'remove_ingredient':
            ri_id = request.POST.get('ri_id')
            try:
                ri = RecipeIngredient.objects.get(pk=ri_id, recipe=recipe)
                name = ri.ingredient.name
                ri.delete()
                messages.success(request, f"Removed '{name}' from recipe.")
            except RecipeIngredient.DoesNotExist:
                messages.error(request, "Ingredient not found.")
                
        return redirect('menu:recipe_manage', pk=pk)

    else:
        recipe_form = RecipeForm(instance=recipe)
        ingredient_form = RecipeIngredientForm()

    context = {
        'menu_item': menu_item,
        'recipe': recipe,
        'recipe_form': recipe_form,
        'ingredient_form': ingredient_form,
        'ingredients': recipe.ingredients.select_related('ingredient').all(),
        'title': f'Recipe: {menu_item.name}'
    }
    return render(request, 'menu/recipe_form.html', context)

# --- Category Management Views (Task 001) ---
from .models import Category
from django.views.generic import CreateView

class CategoryListView(RoleRequiredMixin, ListView):
    allowed_roles = ['MANAGER', 'ADMIN']
    model = Category
    template_name = 'menu/category_list.html'
    context_object_name = 'categories'

class CategoryCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    allowed_roles = ['MANAGER', 'ADMIN']
    model = Category
    fields = ['name', 'description', 'printer_target', 'is_active']
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu:category_list')
    success_message = "Category created successfully."
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create New Category"
        return context

class CategoryUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    allowed_roles = ['MANAGER', 'ADMIN']
    model = Category
    fields = ['name', 'description', 'printer_target', 'is_active']
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu:category_list')
    success_message = "Category updated successfully."
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update Category"
        return context
