from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('', views.report_dashboard, name='dashboard'),
    path('sales/', views.sales_report_view, name='sales_report'),
    path('inventory/', views.inventory_report_view, name='inventory_report'),
    path('waste/', views.waste_report_view, name='waste_report'),
    
    # Task 027
    path('api/chart-data/', views.ChartDataAPIView.as_view(), name='chart_data_api'),
]
