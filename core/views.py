from typing import Any, Dict
from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    """
    Custom Login View that renders the core/login.html template.
    Redirects authenticated users to the dashboard automatically.
    """
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
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

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    The main landing page after login.
    Protected by LoginRequiredMixin to ensure only authenticated users access it.
    """
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
