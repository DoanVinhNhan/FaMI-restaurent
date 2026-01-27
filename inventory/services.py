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
