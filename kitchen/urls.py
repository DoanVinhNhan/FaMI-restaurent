from django.urls import path
from . import views

app_name = 'kitchen'

urlpatterns = [
    # The main KDS Board view
    path('board/', views.kds_board_view, name='kds_board'),
    
    # Endpoint for status updates (HTMX)
    path('item/<int:detail_id>/update/', views.update_item_status, name='update_item_status'),
    path('item/<int:detail_id>/cancel/', views.cancel_item, name='cancel_item'),
    path('item/<int:detail_id>/undo/', views.undo_item_status, name='undo_item'),
    
    # DRF API Endpoints
    path('api/dashboard/', views.KitchenDashboardView.as_view(), name='api_dashboard'),
    path('api/items/<int:pk>/status/', views.KitchenItemStatusView.as_view(), name='api_item_status'),
    
    # Waste Reporting (Task 022)
    path('waste/', views.WasteReportView.as_view(), name='waste_report'),
]
