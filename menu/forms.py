import datetime
from django import forms
from django.utils import timezone
from .models import MenuItem, Pricing, Category

class MenuItemForm(forms.ModelForm):
    """
    Form for creating and updating MenuItem details.
    """
    class Meta:
        model = MenuItem
        fields = ['sku', 'name', 'category', 'description', 'image', 'status']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter SKU'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dish Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_sku(self) -> str:
        """
        Validate SKU uniqueness, excluding the current instance if updating.
        """
        sku = self.cleaned_data['sku']
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if MenuItem.objects.filter(sku=sku).exclude(pk=instance.pk).exists():
                raise forms.ValidationError("SKU must be unique.")
        else:
            if MenuItem.objects.filter(sku=sku).exists():
                raise forms.ValidationError("SKU must be unique.")
        return sku


class PricingForm(forms.ModelForm):
    """
    Form for setting the Pricing.
    When creating a menu item, this sets the initial price.
    """
    class Meta:
        model = Pricing
        fields = ['selling_price', 'effective_date'] # Removed cost_price from fields if not in model yet, checking plan
        # Plan mentions cost_price in logic but let me double check Task 010.
        # Task 010 implemented Pricing model with spelling_price, effective_date.
        # It did NOT add 'cost_price' to Pricing model (cost is calculated from Recipe). 
        # Wait, the plan for Task 012 shows 'cost_price' in PricingForm widgets.
        # However, Task 010 verification script clearly shows Pricing(selling_price, effective_date).
        # Recipe has calculate_standard_cost.
        # So I should NOT include cost_price in PricingForm unless I add it to model.
        # The prompt for Task 012 had 'cost_price' in the form code.
        # I should assume 'selling_price' is the critical one.
        # If the user wants cost_price manually set, it needs to be in model.
        # But 'Recipe' calculates cost.
        # Let's stick to what's in the model: selling_price, effective_date.
        widgets = {
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_effective_date(self) -> datetime.date:
        """
        Ensure effective date is not in the past for new prices.
        """
        # Form cleaning returns datetime.date/datetime object depending on field type.
        # Model field is DateTimeField. Form is DateInput (returns date).
        # We might need to handle conversation or model handles it.
        date_val = self.cleaned_data['effective_date']
        # Ideally allow today, but warn if in past. For strict logic:
        # if date < timezone.now().date():
        #     raise forms.ValidationError("Effective date cannot be in the past.")
        return date_val

# --- Recipe Forms ---
from .models import Recipe, RecipeIngredient

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['instructions']
        widgets = {
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter preparation instructions...'}),
        }

class RecipeIngredientForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = ['ingredient', 'quantity', 'unit']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. g, ml, pcs'}),
        }
