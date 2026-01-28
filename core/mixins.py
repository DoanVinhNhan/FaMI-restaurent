from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure user has one of the allowed roles.
    Set `allowed_roles` in the view class.
    Example: allowed_roles = ['MANAGER', 'CASHIER']
    """
    allowed_roles = []

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Superuser always accesses everything
        if user.is_superuser:
            return True
            
        # Manager usually accesses everything, but let's be explicit in views
        # If view explicitly excludes MANAGER, they can't see it (rare)
        if 'MANAGER' in self.allowed_roles and user.role == 'MANAGER':
            return True
            
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        from django.shortcuts import redirect
        from django.contrib import messages
        from django.urls import reverse
        
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
            
        # User is authenticated but lacks permission
        user = self.request.user
        messages.warning(self.request, "Bạn không có quyền truy cập trang này. Đã chuyển hướng về trang chủ.")
        
        target_url = 'core:login'
        if user.role == 'CASHIER':
            target_url = 'sales:pos_index'
        elif user.role == 'KITCHEN':
            target_url = 'kitchen:kds_board'
        elif user.is_manager() or user.is_inventory_manager() or user.is_superuser or user.role == 'ADMIN':
            target_url = 'core:dashboard'
        # Fallback to Access Denied page to avoid infinite loops if dashboard is also restricted
        # or if user role is unknown
        return redirect('core:access_denied')
