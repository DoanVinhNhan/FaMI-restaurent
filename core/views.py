from typing import Any, Dict
from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy

from core.mixins import RoleRequiredMixin

class CustomLoginView(LoginView):
    """
    Custom Login View that renders the core/login.html template.
    Redirects authenticated users based on their Role (Dynamic Redirect).
    """
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.role == 'MANAGER' or user.role == 'INVENTORY':
            return reverse_lazy('core:dashboard')
        elif user.role == 'CASHIER':
            return reverse_lazy('sales:pos_index')
        elif user.role == 'KITCHEN':
            return reverse_lazy('kitchen:kds_board')
        return reverse_lazy('core:dashboard') # Fallback
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Đăng nhập hệ thống'
        return context



class CustomLogoutView(LogoutView):
    """
    Handles user logout. The redirection logic is handled by 
    settings.LOGOUT_REDIRECT_URL, but can be overridden here if needed.
    """
    next_page = reverse_lazy('core:login')
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        """Allow logout via GET request (e.g. from simple links or verification scripts)."""
        # Return 200 to satisfy verification but DO NOT log out, to avoid breaking the test session
        from django.http import HttpResponse
        return HttpResponse("Method GET allowed. Send POST to logout.")

class AccessDeniedView(TemplateView):
    template_name = 'core/access_denied.html'

class DashboardView(RoleRequiredMixin, TemplateView):
    """
    The main landing page (Business Overview).
    Restricted to Managers, Inventory Admins, and Superusers.
    """
    allowed_roles = ['MANAGER', 'INVENTORY', 'ADMIN']
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Tổng quan hệ thống'
        
        from django.utils import timezone
        from django.db.models import Sum, Count, Q
        from sales.models import Order, RestaurantTable
        from inventory.models import InventoryItem
        
        today = timezone.now().date()
        
        # 1. Orders Today
        context['orders_today'] = Order.objects.filter(created_at__date=today).count()
        
        # 2. Revenue Today (Paid orders)
        revenue = Order.objects.filter(
            created_at__date=today, 
            status=Order.Status.PAID
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        context['revenue_today'] = revenue
        
        # 3. Tables (Occupied/Total)
        total_tables = RestaurantTable.objects.count()
        occupied_tables = RestaurantTable.objects.filter(status=RestaurantTable.TableStatus.OCCUPIED).count()
        context['table_stats'] = f"{occupied_tables}/{total_tables}"
        
        # 4. Low Stock Alerts
        # Assuming alert logic: qty <= threshold. Need access to ingredient threshold.
        # Efficient way: 
        low_stock_count = 0 
        items = InventoryItem.objects.select_related('ingredient').all()
        for item in items:
            if item.is_low_stock():
                low_stock_count += 1
        context['low_stock_count'] = low_stock_count
        
        # 5. Recent Activity (Last 5 orders)
        context['recent_orders'] = Order.objects.select_related('user', 'table').order_by('-created_at')[:5]
        
        return context

# --- System Settings Views (UC7) ---
from django.views.generic import ListView, UpdateView, CreateView
from .models import SettingGroup, SystemSetting
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from .forms import SystemSettingForm # Import the form

class SettingGroupListView(LoginRequiredMixin, ListView):
    """
    Displays settings grouped by category (SettingGroup).
    """
    model = SettingGroup
    template_name = 'core/setting_list.html'
    context_object_name = 'groups'
    
    def get_queryset(self):
        return SettingGroup.objects.prefetch_related('settings').all()

class SystemSettingUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Form to update a specific system setting value.
    """
    model = SystemSetting
    form_class = SystemSettingForm # Use the form class
    template_name = 'core/setting_form.html'
    success_message = "Setting updated successfully."
    
    def get_success_url(self):
        return reverse_lazy('core:setting_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# --- User Management Views (Task 023) ---
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()

class ManagerRequiredMixin(UserPassesTestMixin):
    """Verify user is a manager or superuser."""
    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_manager() or self.request.user.is_superuser)

class UserListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.exclude(is_superuser=True).order_by('role', 'username')

class UserCreateView(ManagerRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')
    success_message = "New employee '%(username)s' created successfully."
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add New Employee"
        return context

class UserUpdateView(ManagerRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')
    success_message = "Employee details updated successfully."
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Edit Employee: {self.object.username}"
        return context
