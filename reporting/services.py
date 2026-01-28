
import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Dict, List, Any, Optional
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.db.models.functions import TruncDate

# Importing models from other apps
from sales.models import Order, OrderDetail
from inventory.models import StockTakeTicket, StockTakeDetail
from kitchen.models import WasteReport

@dataclass
class SalesReportSummary:
    start_date: date
    end_date: date
    total_revenue: Decimal
    total_orders: int
    daily_breakdown: List[Dict[str, Any]]
    top_selling_items: List[Dict[str, Any]]

@dataclass
class InventoryVarianceSummary:
    ticket_id: int
    created_at: datetime
    total_variance_value: Decimal
    items_with_variance: List[Dict[str, Any]]

class ReportController:
    """
    Controller responsible for aggregating data and generating reports.
    Acts as the Business Logic Layer for the Reporting Module.
    """

    @staticmethod
    def validate_params(start_date: date, end_date: date) -> None:
        """
        Validates report parameters.
        Raises ValueError if invalid.
        """
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
        
        # Limit range to prevent overload (Sequence: 'Data quá tải')
        if (end_date - start_date).days > 365:
             raise ValueError("Date range too large. Please limit to 1 year.")

    @staticmethod
    def generate_sales_report(start_date: date, end_date: date) -> SalesReportSummary:
        """
        Generates a sales report for a given date range.
        Aggregates total revenue and groups sales by day.
        Only considers the 'PAID' or 'COMPLETED' equivalent orders.
        """
        # Ensure dates include the full time range for the end date
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

        # Filter Sales
        # Order Status: PAID is the reliable one for revenue
        orders = Order.objects.filter(
            created_at__range=(start_dt, end_dt),
            status__in=[Order.Status.PAID] 
        )

        # 1. Total Aggregates
        aggregates = orders.aggregate(
            total_rev=Sum('total_amount'),
            count=Count('id')
        )
        total_revenue = aggregates['total_rev'] or Decimal('0.00')
        total_orders = aggregates['count'] or 0

        # 2. Daily Breakdown
        daily_data = (
            orders
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(daily_revenue=Sum('total_amount'), daily_count=Count('id'))
            .order_by('date')
        )

        # 3. Top Selling Items (requiring join with OrderDetail)
        # We need to filter OrderDetails belonging to the filtered orders
        top_items = (
            OrderDetail.objects
            .filter(order__in=orders)
            .values('menu_item__name')  # Group by Item Name
            .annotate(total_qty=Sum('quantity'), total_sales=Sum(F('quantity') * F('unit_price')))
            .order_by('-total_qty')[:10]  # Top 10
        )

        return SalesReportSummary(
            start_date=start_date,
            end_date=end_date,
            total_revenue=total_revenue,
            total_orders=total_orders,
            daily_breakdown=list(daily_data),
            top_selling_items=list(top_items)
        )

    @staticmethod
    def generate_inventory_variance_report(start_date: date, end_date: date) -> List[InventoryVarianceSummary]:
        """
        Generates a report on Stock Taking discrepancies.
        Fetches completed StockTakeTickets and details variances.
        """
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

        tickets = StockTakeTicket.objects.filter(
            created_at__range=(start_dt, end_dt),
            status='COMPLETED'
        ).prefetch_related('details__ingredient')

        report_data = []

        for ticket in tickets:
            details = ticket.details.all()
            
            # Filter only items with variance != 0
            variance_items = []
            for d in details:
                if d.variance != 0:
                    variance_items.append({
                        'ingredient': d.ingredient.name,
                        'system_qty': d.snapshot_quantity,
                        'actual_qty': d.actual_quantity,
                        'variance': d.variance,
                        'reason': d.reason or "N/A"
                    })

            summary = InventoryVarianceSummary(
                ticket_id=ticket.ticket_id,
                created_at=ticket.created_at,
                total_variance_value=ticket.variance_total_value,
                items_with_variance=variance_items
            )
            report_data.append(summary)

        return report_data

    @staticmethod
    def generate_waste_report(start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Aggregates kitchen waste reports.
        """
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

        # We assume waste reports have 'reason' (FK) and 'quantity'.
        # We want to aggregate by reason.
        waste_logs = WasteReport.objects.filter(
            reported_at__range=(start_dt, end_dt)
        ).values('reason__code', 'reason__description').annotate(
            total_qty=Sum('quantity'),
            total_loss=Sum('loss_value')
        ).order_by('reason__code')

        return list(waste_logs)

    @staticmethod
    def export_sales_to_csv(summary: SalesReportSummary) -> Any:
        """
        Converts Sales Report Summary to a CSV file object.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Sales Report', f"{summary.start_date} to {summary.end_date}"])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Total Revenue', summary.total_revenue])
        writer.writerow(['Total Orders', summary.total_orders])
        writer.writerow([])

        # Daily Breakdown
        writer.writerow(['Date', 'Orders', 'Revenue'])
        for day in summary.daily_breakdown:
            writer.writerow([day['date'], day['daily_count'], day['daily_revenue']])
        
        writer.writerow([])
        
        # Top Items
        writer.writerow(['Item Name', 'Quantity Sold', 'Total Sales'])
        for item in summary.top_selling_items:
            writer.writerow([item['menu_item__name'], item['total_qty'], item['total_sales']])

        return output.getvalue()
