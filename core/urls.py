from django.urls import path
from .views import CustomLoginView, CustomLogoutView, DashboardView
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication URLs
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # Dashboard URL
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Optional: Root redirects to dashboard (handled in project urls or here)
    path('', DashboardView.as_view(), name='home'),
    
    # System Settings (UC7)
    path('settings/', views.SettingGroupListView.as_view(), name='setting_list'),
    path('settings/<str:pk>/edit/', views.SystemSettingUpdateView.as_view(), name='setting_edit'),

    # User Management (HR)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<uuid:pk>/edit/', views.UserUpdateView.as_view(), name='user_model_edit'),
    
    # Access Denied
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
]
