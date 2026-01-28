from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # List view
    path('', views.MenuItemListView.as_view(), name='menu_list'),
    
    # Create view (Function-based to handle multi-form)
    path('create/', views.menu_item_create_view, name='menu_create'),
    
    # Update view
    path('items/<int:pk>/edit/', views.menu_item_update_view, name='menu_item_edit'),
    
    # Soft Delete view
    # Soft Delete view
    path('<int:pk>/delete/', views.menu_item_soft_delete_view, name='menu_delete'),

    # Recipe Management (UC: Manage Recipes)
    path('items/<int:pk>/recipe/', views.menu_recipe_view, name='recipe_manage'),
]
