from django.urls import path
from .views import (
    IngredientListView, 
    IngredientCreateView, 
    IngredientUpdateView, 
    IngredientListView,
    IngredientCreateView,
    IngredientUpdateView,
    IngredientDeleteView,
    # New imports for Task 008 and Task 025 views
    inventory_dashboard,
    adjust_stock,
    inventory_logs,
    stock_take_list,
    stock_take_create,
    stock_take_detail,
)

app_name = 'inventory'

urlpatterns = [
    # Existing Ingredient URLs
    path('ingredients/', IngredientListView.as_view(), name='ingredient_list'),
    path('ingredients/add/', IngredientCreateView.as_view(), name='ingredient_add'),
    path('ingredients/<int:pk>/edit/', IngredientUpdateView.as_view(), name='ingredient_edit'),
    path('ingredients/<int:pk>/delete/', IngredientDeleteView.as_view(), name='ingredient_delete'),

    # Task 008 Views
    path('dashboard/', inventory_dashboard, name='dashboard'),
    path('items/<int:pk>/adjust/', adjust_stock, name='adjust_stock'),
    path('logs/', inventory_logs, name='inventory_logs'),

    # Task 025 (Stock Take)
    path('stocktake/', stock_take_list, name='stock_take_list'),
    path('stocktake/create/', stock_take_create, name='stock_take_create'),
    path('stocktake/<uuid:ticket_id>/', stock_take_detail, name='stock_take_detail'),
]
