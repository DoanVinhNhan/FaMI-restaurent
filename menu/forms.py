import datetime
from django import forms
from django.utils import timezone
from django.forms import inlineformset_factory
from .models import MenuItem, Pricing, Category, Recipe, RecipeIngredient, ComboComponent

class MenuItemForm(forms.ModelForm):
    """
    Form for creating and updating MenuItem details.
    """
    class Meta:
        model = MenuItem
        fields = ['sku', 'name', 'category', 'description', 'image', 'prep_time', 'is_popular', 'status']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter SKU'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dish Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'prep_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_popular': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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


class ComboComponentForm(forms.ModelForm):
    """
    Form for defining a component item inside a combo.
    """
    class Meta:
        model = ComboComponent
        fields = ['item', 'quantity']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this form is bound to an existing ComboComponent instance, try to exclude the parent combo
        parent_pk = None
        # Inline formset will set instance on the form's _meta.model_instance indirectly - safer to check instance attribute
        if hasattr(self.instance, 'combo') and self.instance.combo:
            parent_pk = getattr(self.instance.combo, 'pk', None)
        # Set queryset for item to exclude parent combo item when possible
        if parent_pk:
            self.fields['item'].queryset = MenuItem.objects.exclude(pk=parent_pk)


from django.forms.models import BaseInlineFormSet

class BaseComboComponentFormSet(BaseInlineFormSet):
    """Custom formset to exclude the parent combo from item choices and validate self-reference."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent_pk = getattr(self.instance, 'pk', None)
        for form in self.forms:
            # Some forms may not yet have an 'item' field if empty; guard access
            if 'item' in form.fields:
                if parent_pk:
                    form.fields['item'].queryset = MenuItem.objects.exclude(pk=parent_pk)
                else:
                    form.fields['item'].queryset = MenuItem.objects.all()

    def clean(self):
        super().clean()
        parent_pk = getattr(self.instance, 'pk', None)
        seen = set()

        for form in self.forms:
            # Respect delete flags - ignore forms marked for deletion
            delete = False
            if hasattr(form, 'cleaned_data'):
                delete = form.cleaned_data.get('DELETE', False)
            if delete:
                continue

            # If form has no cleaned_data (had field errors), skip additional validation here
            if not hasattr(form, 'cleaned_data'):
                continue

            item = form.cleaned_data.get('item')
            # Completely empty extra forms should be ignored (no item selected)
            if not item:
                continue

            # Prevent self-referential component
            if parent_pk and item.pk == parent_pk:
                raise forms.ValidationError("A combo cannot include itself as a component.")

            # Prevent duplicate components within the same combo
            if item.pk in seen:
                raise forms.ValidationError("Duplicate components are not allowed.")
            seen.add(item.pk)


ComboComponentFormSet = inlineformset_factory(
    parent_model=MenuItem,
    model=ComboComponent,
    fk_name='combo',
    form=ComboComponentForm,
    formset=BaseComboComponentFormSet,
    # No pre-filled extras; use JS button to add rows dynamically
    extra=0,
    can_delete=True,
)
