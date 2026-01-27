from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('tables/', views.TableListView.as_view(), name='table_list'),
    path('tables/create/', views.TableCreateView.as_view(), name='table_create'),
    path('tables/<int:pk>/edit/', views.TableUpdateView.as_view(), name='table_edit'),
    path('tables/<int:pk>/delete/', views.TableDeleteView.as_view(), name='table_delete'),

    # POS / Cashier Interface
    path('pos/', views.pos_index, name='pos_index'),
    path('pos/table/<int:table_id>/', views.pos_table_detail, name='pos_table_detail'),
    
    # HTMX Actions
    path('pos/table/<int:table_id>/add/<int:item_id>/', views.add_to_cart, name='pos_add_item'),
    path('pos/table/<int:table_id>/remove/<int:detail_id>/', views.remove_from_cart, name='pos_remove_item'),
    
    # Submit Action
    path('pos/table/<int:table_id>/submit/', views.submit_order, name='pos_submit_order'),
]
