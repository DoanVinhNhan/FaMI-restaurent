from datetime import date, timedelta
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.dateparse import parse_date
from django.contrib import messages
from .services import ReportController

# Basic access check
def is_reporting_viewer(user):
    # Manager or Inventory Manager only
    return user.is_authenticated and (user.role in ['MANAGER', 'INVENTORY'] or user.is_superuser)

@login_required
@user_passes_test(is_reporting_viewer)
def report_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Renders the main dashboard for selecting reports.
    Default range is last 30 days.
    """
    today = date.today()
    start_date = today - timedelta(days=30)
    
    context = {
        'default_start': start_date.isoformat(),
        'default_end': today.isoformat()
    }
    return render(request, 'reporting/dashboard.html', context)

@login_required
@user_passes_test(is_reporting_viewer)
def sales_report_view(request: HttpRequest) -> HttpResponse:
    """
    HTMX or Standard view to render sales report table.
    """
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')
    export = request.GET.get('export')

    today = date.today()
    if not start_str or not end_str:
        # Fallback to defaults
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)

    try:
        ReportController.validate_params(start_date, end_date)
        summary = ReportController.generate_sales_report(start_date, end_date)
        
        # Check for empty data
        if summary.total_orders == 0:
             messages.info(request, "No data found for the selected range.")
             
    except ValueError as e:
        messages.error(request, str(e))
        # Return empty summary or render error state
        summary = None 

    if export == 'csv' and summary:
        csv_content = ReportController.export_sales_to_csv(summary)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.csv"'
        return response

    context = {'summary': summary}
    return render(request, 'reporting/partials/sales_results.html', context)

@login_required
@user_passes_test(is_reporting_viewer)
def sales_drilldown_view(request: HttpRequest) -> HttpResponse:
    """
    HTMX view that returns a partial table of Orders related to a given menu item in the date range.
    Accepts GET params: start_date, end_date, item (menu item name), page
    """
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')
    item = request.GET.get('item')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))

    today = date.today()
    if not start_str or not end_str:
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)

    try:
        ReportController.validate_params(start_date, end_date)
        orders_page = ReportController.get_orders_for_item(start_date, end_date, item, page=page, per_page=per_page)
    except ValueError as e:
        messages.error(request, str(e))
        orders_page = None

    context = {'orders_page': orders_page, 'item': item}
    return render(request, 'reporting/partials/sales_drilldown.html', context)

@login_required
@user_passes_test(is_reporting_viewer)
def inventory_report_view(request: HttpRequest) -> HttpResponse:
    """
    View to render inventory variance report.
    """
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')

    if not start_str or not end_str:
        today = date.today()
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)

    tickets = ReportController.generate_inventory_variance_report(start_date, end_date)

    context = {'tickets': tickets}
    return render(request, 'reporting/partials/inventory_results.html', context)

@login_required
@user_passes_test(is_reporting_viewer)
def waste_report_view(request: HttpRequest) -> HttpResponse:
    """
    View to render waste analysis.
    """
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')
    
    if not start_str or not end_str:
        today = date.today()
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)
    
    waste_data = ReportController.generate_waste_report(start_date, end_date)
    
    context = {'waste_data': waste_data}
    return render(request, 'reporting/partials/waste_results.html', context)


# --- Task 027 (Visual Reports) ---
from django.views import View
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import datetime
from sales.models import Order, OrderDetail

class ChartDataAPIView(LoginRequiredMixin, View):
    """
    API Endpoint to return JSON data for Chart.js.
    """
    def get(self, request: HttpRequest) -> JsonResponse:
        try:
            days_param = request.GET.get('days', 30)
            days = int(days_param)
        except ValueError:
            days = 30

        start_date = timezone.now().date() - datetime.timedelta(days=days)

        # 1. Revenue
        revenue_queryset = (
            Order.objects.filter(
                status=Order.Status.PAID,
                created_at__date__gte=start_date
            )
            .annotate(date=TruncDay('created_at'))
            .values('date')
            .annotate(total_revenue=Sum('total_amount'))
            .order_by('date')
        )

        revenue_labels = []
        revenue_data = []

        for entry in revenue_queryset:
            revenue_labels.append(entry['date'].strftime('%Y-%m-%d'))
            revenue_data.append(float(entry['total_revenue'] or 0.0))

        # 2. Top Items
        top_items_queryset = (
            OrderDetail.objects.filter(
                order__status=Order.Status.PAID,
                order__created_at__date__gte=start_date
            )
            .values('menu_item__name')
            .annotate(total_qty=Sum('quantity'))
            .order_by('-total_qty')[:5]
        )

        item_labels = []
        item_data = []

        for entry in top_items_queryset:
            name = entry.get('menu_item__name') or "Unknown Item"
            item_labels.append(name)
            item_data.append(int(entry['total_qty'] or 0))

        data = {
            "revenue_chart": {
                "labels": revenue_labels,
                "data": revenue_data,
            },
            "top_items_chart": {
                "labels": item_labels,
                "data": item_data,
            }
        }
        return JsonResponse(data)
