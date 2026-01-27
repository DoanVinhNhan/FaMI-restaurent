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

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    The main landing page after login.
    Protected by LoginRequiredMixin to ensure only authenticated users access it.
    """
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Add summary data here later (e.g., total orders today)
        context['page_title'] = 'Tổng quan hệ thống'
        return context
