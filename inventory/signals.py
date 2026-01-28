import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import InventoryItem

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InventoryItem)
def inventoryitem_post_save(sender, instance, created, **kwargs):
    """When inventory levels change, re-evaluate menu items that depend on this ingredient
    and set their status to OUT_OF_STOCK or back to ACTIVE depending on availability.
    """
    try:
        # Local imports to avoid circular import at module load
        from menu.models import MenuItem
        from inventory.services import InventoryService

        related_menu_items = MenuItem.objects.filter(recipe__ingredients__ingredient=instance.ingredient).distinct()

        for menu_item in related_menu_items:
            try:
                available = InventoryService.check_availability(menu_item, 1)
            except Exception as e:
                logger.exception("Error checking availability for %s: %s", menu_item, e)
                continue

            if not available and menu_item.status != MenuItem.ItemStatus.OUT_OF_STOCK:
                menu_item.status = MenuItem.ItemStatus.OUT_OF_STOCK
                menu_item.save(update_fields=['status', 'updated_at'])
                logger.info("Marked %s as OUT_OF_STOCK due to ingredient %s", menu_item, instance.ingredient)

            elif available and menu_item.status == MenuItem.ItemStatus.OUT_OF_STOCK:
                # Only revert status if it was previously marked out of stock.
                menu_item.status = MenuItem.ItemStatus.ACTIVE
                menu_item.save(update_fields=['status', 'updated_at'])
                logger.info("Re-activated %s as ingredients replenished", menu_item)

    except Exception as e:
        logger.exception("inventory.signals.inventoryitem_post_save failed: %s", e)
