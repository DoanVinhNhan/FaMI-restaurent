from decimal import Decimal
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from inventory.models import InventoryItem, Ingredient
from kitchen.models import WasteReport, ReasonCode
# Delayed import or direct import depending on circular dependency risk
# Usually Service layer can import models freely as long as models don't import services at top level.
from menu.models import MenuItem, Recipe

class WasteService:
    @staticmethod
    @transaction.atomic
    def report_waste(user, item_type: str, item_id: int, quantity: float, reason_id: str) -> WasteReport:
        """
        Processes a waste report.
        
        Args:
            user: The user reporting the waste.
            item_type: 'ingredient' or 'menu_item'.
            item_id: ID of the Ingredient or MenuItem.
            quantity: Amount wasted.
            reason_id: The code of the ReasonCode.
            
        Returns:
            The created WasteReport instance.
        """
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")

        try:
            reason = ReasonCode.objects.get(code=reason_id)
        except ReasonCode.DoesNotExist:
            raise ValidationError(f"Invalid reason code: {reason_id}")

        qty_decimal = Decimal(str(quantity))
        total_loss = Decimal('0.00')
        target_object = None
        target_content_type = None

        if item_type == 'ingredient':
            # Direct deduction
            try:
                ingredient = Ingredient.objects.get(pk=item_id)
                target_object = ingredient
                target_content_type = ContentType.objects.get_for_model(Ingredient)
                
                # Update Inventory
                inv_item, _ = InventoryItem.objects.get_or_create(ingredient=ingredient)
                inv_item.quantity_on_hand -= qty_decimal
                inv_item.save()
                
                # Calculate loss
                total_loss = ingredient.cost_per_unit * qty_decimal
                
            except Ingredient.DoesNotExist:
                raise ValidationError(f"Ingredient with ID {item_id} not found.")

        elif item_type == 'menu_item':
            # BOM Explosion logic
            try:
                menu_item = MenuItem.objects.get(pk=item_id)
                target_object = menu_item
                target_content_type = ContentType.objects.get_for_model(MenuItem)
                
                # Find Recipe
                try:
                    recipe = Recipe.objects.get(menu_item=menu_item)
                    # Deduct ingredients based on recipe
                    for component in recipe.ingredients.all():
                        # component is RecipeIngredient
                        required_qty = component.quantity * qty_decimal
                        
                        inv_item, _ = InventoryItem.objects.get_or_create(ingredient=component.ingredient)
                        inv_item.quantity_on_hand -= required_qty
                        inv_item.save()
                        
                        # Add to loss value
                        total_loss += component.ingredient.cost_per_unit * required_qty
                        
                except Recipe.DoesNotExist:
                    # If no recipe exists, we just record the report but can't deduct inventory accurately
                    pass
                    
            except MenuItem.DoesNotExist:
                raise ValidationError(f"Menu Item with ID {item_id} not found.")
        
        else:
            raise ValidationError("Invalid item type. Must be 'ingredient' or 'menu_item'.")

        # Create the log
        report = WasteReport.objects.create(
            actor=user,
            content_type=target_content_type,
            object_id=target_object.pk,
            quantity=qty_decimal,
            reason=reason,
            loss_value=total_loss
        )
        
        return report

class InventoryService:
    @staticmethod
    def deduct_ingredients_for_order(order):
        """
        Deducts inventory based on the items in the paid order.
        Assumes BOM/Recipe logic.
        """
        # Avoid circular imports inside method if needed, or rely on top-level
        from sales.models import OrderDetail
        
        # Prefetch to minimize queries
        details = OrderDetail.objects.filter(order=order).select_related('menu_item', 'menu_item__recipe')
        print(f"DEBUG: Deducting Inventory for Order #{order.id} with {details.count()} items.")
        
        for detail in details:
            menu_item = detail.menu_item
            if not hasattr(menu_item, 'recipe'):
                continue
                
            recipe = menu_item.recipe
            # access ingredients through RecipeIngredient related_name='ingredients' (from Recipe model)
            # Actually RecipeIngredient has recipe=ForeignKey(Recipe, related_name='ingredients')
            
            for component in recipe.ingredients.all():
                # component is RecipeIngredient
                # total quantity needed = order_qty * component_qty_per_unit
                total_needed = Decimal(detail.quantity) * component.quantity
                
                # Fetch Inventory Item
                # We use get_or_create to be safe, though ideally it should exist
                inv_item, _ = InventoryItem.objects.get_or_create(ingredient=component.ingredient)
                inv_item.quantity_on_hand -= total_needed
                inv_item.save()

    @staticmethod
    def check_availability(menu_item, quantity: int) -> bool:
        """
        Checks if there is enough inventory to fulfill the order for a specific menu item.
        Returns True if available, False otherwise.
        """
        if not hasattr(menu_item, 'recipe'):
            # If no recipe, we assume it's always available (or handle differently)
            # For strict control, maybe return False. But for now, True.
            return True
            
        recipe = menu_item.recipe
        qty_decimal = Decimal(quantity)
        
        for component in recipe.ingredients.all():
            required_qty = component.quantity * qty_decimal
            
            try:
                inv_item = InventoryItem.objects.get(ingredient=component.ingredient)
                if inv_item.quantity_on_hand < required_qty:
                    return False
            except InventoryItem.DoesNotExist:
                # If ingredient not tracked in inventory, assume 0 or treat as critical missing
                return False
                
        return True

    @staticmethod
    def deduct_ingredients_for_item(order_detail):
        """
        Deducts inventory for a single OrderDetail item.
        Used when Kitchen starts cooking a specific dish.
        """
        menu_item = order_detail.menu_item
        print(f"DEBUG: Attempting deduction for {menu_item.name} (ID: {menu_item.id})")
        
        try:
            recipe = menu_item.recipe
        except Exception as e:
            print(f"DEBUG: No recipe found for {menu_item.name}. Skipping deduction. Error: {e}")
            return

        qty_decimal = Decimal(order_detail.quantity)
        print(f"DEBUG: Found recipe {recipe.id}. Deducting for Qty: {qty_decimal}")

        for component in recipe.ingredients.all():
            total_needed = qty_decimal * component.quantity
            
            inv_item, _ = InventoryItem.objects.get_or_create(ingredient=component.ingredient)
            inv_item.quantity_on_hand -= total_needed
            inv_item.save()
            print(f"DEBUG: Deducted {total_needed} {component.unit} of {component.ingredient.name} (New Level: {inv_item.quantity_on_hand})")

    @staticmethod
    def get_low_stock_items():
        """
        Returns a list of InventoryItems that are below their ingredient's alert threshold.
        """
        # Efficient query using F expressions if needed, or python loop given scale
        # We need InventoryItems where quantity_on_hand <= ingredient.alert_threshold
        # And threshold > 0 (to avoid alerts for items we don't track or have 0 threshold)
        
        from django.db.models import F
        
        low_stock = InventoryItem.objects.select_related('ingredient').filter(
            ingredient__alert_threshold__gt=0,
            quantity_on_hand__lte=F('ingredient__alert_threshold')
        )
        return low_stock


