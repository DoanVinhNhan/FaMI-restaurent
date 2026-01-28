from django.core.management.base import BaseCommand
from menu.models import MenuItem
from inventory.services import InventoryService

class Command(BaseCommand):
    help = 'Re-evaluate menu items stock status based on current inventory levels.'

    def handle(self, *args, **options):
        items = MenuItem.objects.all()
        changed = 0
        for item in items:
            try:
                # Only evaluate items that have recipes or are tracked
                available = item.is_stock_available(1)
                if not available and item.status != MenuItem.ItemStatus.OUT_OF_STOCK:
                    item.status = MenuItem.ItemStatus.OUT_OF_STOCK
                    item.save(update_fields=['status', 'updated_at'])
                    changed += 1
                elif available and item.status == MenuItem.ItemStatus.OUT_OF_STOCK:
                    item.status = MenuItem.ItemStatus.ACTIVE
                    item.save(update_fields=['status', 'updated_at'])
                    changed += 1
            except Exception as e:
                self.stdout.write(f"Error evaluating {item}: {e}")
        self.stdout.write(f"Done. Updated {changed} items.")
