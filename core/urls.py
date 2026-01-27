from django.urls import path
from .views import CustomLoginView, CustomLogoutView, DashboardView

app_name = 'core'

urlpatterns = [
    # Authentication URLs
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # Dashboard URL
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Optional: Root redirects to dashboard (handled in project urls or here)
    path('', DashboardView.as_view(), name='home'),
]
