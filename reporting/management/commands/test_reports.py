
from django.core.management.base import BaseCommand
from datetime import date, timedelta
from reporting.services import ReportController
from decimal import Decimal

class Command(BaseCommand):
    help = 'Test Report Controller Logic'

    def handle(self, *args, **kwargs):
        self.stdout.write("Testing Sales Report Generation...")
        
        # Test range
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        try:
            summary = ReportController.generate_sales_report(start_date, end_date)
            self.stdout.write(self.style.SUCCESS(f"Sales Report Generated Successfully"))
            self.stdout.write(f"Total Revenue: {summary.total_revenue}")
            self.stdout.write(f"Total Orders: {summary.total_orders}")
            self.stdout.write(f"Breakdown Items: {len(summary.daily_breakdown)}")
            
            # Simulate CSV Export
            csv_data = ReportController.export_sales_to_csv(summary)
            if "Sales Report" in str(csv_data):
                self.stdout.write(self.style.SUCCESS("CSV Export Logic Verified"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sales Report Failed: {str(e)}"))

        self.stdout.write("-" * 30)
        self.stdout.write("Testing Inventory Report Generation...")
        
        try:
            tickets = ReportController.generate_inventory_variance_report(start_date, end_date)
            self.stdout.write(self.style.SUCCESS(f"Inventory Report Generated Successfully"))
            self.stdout.write(f"Tickets Found: {len(tickets)}")
            if len(tickets) > 0:
                self.stdout.write(f"First Ticket Variances: {len(tickets[0].items_with_variance)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Inventory Report Failed: {str(e)}"))

        self.stdout.write("-" * 30)
        self.stdout.write("Testing Waste Report Generation...")
        try:
            waste = ReportController.generate_waste_report(start_date, end_date)
            self.stdout.write(self.style.SUCCESS(f"Waste Report Generated Successfully"))
            self.stdout.write(f"Waste Groupings Found: {len(waste)}")
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Waste Report Failed: {str(e)}"))
