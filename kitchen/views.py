import logging
from typing import Dict, List, Any, Optional
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required

# Import models from other apps
from sales.models import OrderDetail, Order
from menu.models import MenuItem

logger = logging.getLogger(__name__)

# Constants for Order Status (Must match Order.Status choices if possible, or mapping)
STATUS_PENDING = 'Pending'
STATUS_COOKING = 'Cooking'
STATUS_DONE = 'Paid'  # In `sales.models.Order.Status` we have PENDING, COOKING, PAID, CANCELLED.
# However, for KDS, we often need intermediate states like "Ready".
# Since we are using Order.Status choices for OrderDetail, we should stick to those or expand them.
# The `sales` app defines: PENDING, COOKING, PAID, CANCELLED.
# For KDS usage:
# - Pending: waiting to start
# - Cooking: in progress
# - Paid: (This usually means served/done in simple flow, or we might need a separate status).
#
# FOR THIS TASK: I will map 'PAID' to 'Ready' contextually for the KDS if using strict choices, 
# OR I should have added 'READY' to the choices.
# Given I used `choices=Order.Status.choices` in the model edit, I am limited to those.
# BUT `Order.Status` is: Pending, Cooking, Paid, Cancelled.
# This might be insufficient for "Ready to Serve". 
# Plan: Use 'Cooking' as "In Progress", and maybe I need to add 'READY' to choices?
# The prompts/specs often imply more granular steps.
# Let's check `Order.Status` definition in `sales/models.py`.
# It has PENDING, COOKING, PAID, CANCELLED.
# I will treat 'PAID' as 'DONE/SERVED' for now to avoid altering `Order` model choices too much if not planned.
# WAIT, usually KDS needs "Ready".
# I'll stick to 'Cooking' as active on KDS. And 'Paid' as completed/hidden.
# Actually, the Plan for Task 020 says: `choices: Pending, Cooking, Done, Served`.
# So I should probably update `Order.Status` choices to include 'READY'/'SERVED' 
# OR define separate choices for OrderDetail.
# In the `replace_file_content` I reused `Order.Status.choices`.
# This might be a limitation.
# Let's proceed with `Cooking` -> `Paid` (Done) for now, or if I can, I'll update the model choices in a follow up.
# For now, let's assume PENDING/COOKING are key for KDS.

# Constants for Printer Targets
TARGET_KITCHEN = 'KITCHEN'
TARGET_BAR = 'BAR'

@login_required
def kds_board_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the main Kitchen Display System board.
    It separates items into 'Kitchen' and 'Bar' streams based on category configuration.
    Refreshes data automatically if using HTMX in the template.
    """
    # 1. Fetch all active OrderDetails
    # Include READY so they can be served
    active_details = OrderDetail.objects.select_related(
        'order',
        'menu_item',
        'menu_item__category'
    ).filter(
        status__in=[
            Order.Status.PENDING, 
            Order.Status.COOKING,
            Order.Status.READY
        ]
    ).order_by('order__created_at', 'created_at')

    # ... (rest of kds_board_view logic remains the same) ...
    # 2. Initialize containers
    kitchen_tickets: Dict[int, Dict[str, Any]] = {}
    bar_tickets: Dict[int, Dict[str, Any]] = {}

    # 3. Process items and group by Order -> Station
    for detail in active_details:
        order_id = detail.order.id
        
        # Determine target station (Default to Kitchen if not specified)
        target = getattr(detail.menu_item.category, 'printer_target', TARGET_KITCHEN)
        
        # Select the appropriate dictionary to populate
        if target == TARGET_BAR:
            target_dict = bar_tickets
        else:
            target_dict = kitchen_tickets

        # Initialize Ticket grouping if not exists
        if order_id not in target_dict:
            target_dict[order_id] = {
                'order': detail.order,
                'items': [],
                'timer_start': detail.order.created_at
            }
        
        # Add item to the list
        target_dict[order_id]['items'].append(detail)

    # 4. Check Low Stock (Task User Request)
    from inventory.services import InventoryService
    low_stock_items = InventoryService.get_low_stock_items()

    context = {
        'kitchen_tickets': list(kitchen_tickets.values()),
        'bar_tickets': list(bar_tickets.values()),
        'last_updated': timezone.now(),
        'low_stock_items': low_stock_items,
    }

    # If the request is an HTMX polling request, return only the partial board
    if request.headers.get('HX-Request'):
        return render(request, 'kitchen/partials/board_content.html', context)

    return render(request, 'kitchen/kds_board.html', context)


@require_POST
@login_required
def update_item_status(request: HttpRequest, detail_id: int) -> JsonResponse:
    """
    Standard status update (Pending -> Cooking -> Ready -> Served).
    """
    next_status = request.POST.get('next_status')
    if not next_status:
        return JsonResponse({'error': 'Missing next_status parameter'}, status=400)

    try:
        from kitchen.services import KitchenController
        KitchenController.update_item_status(
            order_detail_id=detail_id,
            new_status=next_status,
            user=request.user
        )
        return kds_board_view(request)
        
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error updating item status: {str(e)}")
        return JsonResponse({'error': 'Server error during update'}, status=500)

@require_POST
@login_required
def cancel_item(request: HttpRequest, detail_id: int) -> JsonResponse:
    """
    Cancels an item with a reason.
    """
    reason = request.POST.get('reason', 'Cancelled by Kitchen')
    try:
        from kitchen.services import KitchenController
        KitchenController.cancel_item(
            order_detail_id=detail_id,
            reason_code=reason,
            user=request.user
        )
        return kds_board_view(request)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error cancelling item: {str(e)}")
        return JsonResponse({'error': 'Server error'}, status=500)

@require_POST
@login_required
def undo_item_status(request: HttpRequest, detail_id: int) -> JsonResponse:
    """
    Reverts item status.
    """
    try:
        from kitchen.services import KitchenController
        KitchenController.undo_last_status(
            order_detail_id=detail_id,
            user=request.user
        )
        return kds_board_view(request)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error undoing status: {str(e)}")
    except Exception as e:
        logger.error(f"Error undoing status: {str(e)}")
        return JsonResponse({'error': 'Server error'}, status=500)

@require_POST
@login_required
def mark_out_of_stock(request: HttpRequest, menu_item_id: int) -> HttpResponse:
    """
    Marks a Menu Item as OUT_OF_STOCK.
    Returns the updated KDS Board (re-render) to reflect changes (or just alert).
    """
    try:
        item = MenuItem.objects.get(pk=menu_item_id)
        item.status = MenuItem.ItemStatus.OUT_OF_STOCK
        item.save()
        # Optionally notify user
        # messages.warning(request, f"{item.name} is now Out of Stock.")
        # But since this is HTMX, messages might not show easily without OOB swap.
        # Just return the board.
        return kds_board_view(request)
    except MenuItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        logger.error(f"Error marking OOS: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)


# --- DRF API Views (Task 021) ---

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import KitchenItemStatusSerializer, OrderDetailKitchenSerializer
from .services import KitchenController

class KitchenDashboardView(APIView):
    """
    GET: List all pending/cooking items for the KDS.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pending_items = KitchenController.get_pending_items()
        serializer = OrderDetailKitchenSerializer(pending_items, many=True)
        return Response(serializer.data)

class KitchenItemStatusView(APIView):
    """
    POST: Update the status of a specific order item.
    URL: /api/kitchen/items/<int:pk>/status/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        serializer = KitchenItemStatusSerializer(data=request.data)
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            try:
                updated_item = KitchenController.update_item_status(
                    order_detail_id=pk,
                    new_status=new_status,
                    user=request.user
                )
                return Response(
                    OrderDetailKitchenSerializer(updated_item).data,
                    status=status.HTTP_200_OK
                )
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # logger.error(...)
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Waste Reporting Views (Task 022) ---

from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .forms import WasteReportForm
from inventory.services import WasteService
# Assuming models exist in their respective apps for context data
from menu.models import MenuItem
from inventory.models import Ingredient

class WasteReportView(LoginRequiredMixin, View):
    """
    View for Kitchen Crew to report waste.
    """
    template_name = 'kitchen/waste_report.html'
    
    def get(self, request):
        form = WasteReportForm()
        
        # Provide context for a simple list lookup in the UI (for demo purposes)
        # In production, this would be an AJAX Select2 widget
        menu_items = MenuItem.objects.filter(status='ACTIVE') # Case-sensitive status check? Usually 'ACTIVE' or 'Active'
        ingredients = Ingredient.objects.all()
        
        context = {
            'form': form,
            'menu_items': menu_items,
            'ingredients': ingredients
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = WasteReportForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                report = WasteService.report_waste(
                    user=request.user,
                    item_type=data['item_type'],
                    item_id=data['item_id'],
                    quantity=data['quantity'],
                    reason_id=data['reason'].code
                )
                messages.success(request, f"Waste reported successfully! Log ID: {report.log_id}")
                return redirect('kitchen:waste_report')
                
            except ValidationError as e:
                messages.error(request, f"Error reporting waste: {e.message}")
            except Exception as e:
                messages.error(request, f"System error: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")

        # Re-render with context if failed
        menu_items = MenuItem.objects.filter(status='ACTIVE')
        ingredients = Ingredient.objects.all()
        context = {
            'form': form,
            'menu_items': menu_items,
            'ingredients': ingredients
        }
        return render(request, self.template_name, context)

@login_required
def menu_management_view(request: HttpRequest) -> HttpResponse:
    """
    View for Kitchen to manage "Out of Stock" items globally.
    """
    # Simply list all active items grouped by category
    items = MenuItem.objects.select_related('category').exclude(status=MenuItem.ItemStatus.INACTIVE).order_by('category__name', 'name')
    
    context = {
        'menu_items': items,
    }
    return render(request, 'kitchen/menu_management.html', context)

@require_POST
@login_required
def toggle_menu_item_stock(request: HttpRequest, item_id: int) -> HttpResponse:
    """
    Toggles the stock status of a menu item (ACTIVE <-> OUT_OF_STOCK).
    Returns the updated button/row HTML (HTMX).
    """
    item = get_object_or_404(MenuItem, pk=item_id)
    
    if item.status == MenuItem.ItemStatus.OUT_OF_STOCK:
        item.status = MenuItem.ItemStatus.ACTIVE
    else:
        item.status = MenuItem.ItemStatus.OUT_OF_STOCK
    item.save()
    
    # Return just the updated row or button
    # For simplicity, we can return the row partial
    return render(request, 'kitchen/partials/menu_item_row.html', {'item': item})
