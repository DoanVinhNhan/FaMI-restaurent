from django import forms
from kitchen.models import ReasonCode

class WasteReportForm(forms.Form):
    ITEM_TYPE_CHOICES = [
        ('menu_item', 'Menu Item (Finished Dish)'),
        ('ingredient', 'Raw Ingredient'),
    ]

    item_type = forms.ChoiceField(
        choices=ITEM_TYPE_CHOICES, 
        label="What was wasted?",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # This will be populated dynamically via AJAX in a real app, 
    # but for simplicity we assume the user enters ID or we load a list.
    # Here we use an IntegerField for ID input for the basic implementation.
    item_id = forms.IntegerField(
        label="Item ID / Scan Barcode", 
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter ID'})
    )
    
    quantity = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0.01, 
        label="Quantity Wasted",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason = forms.ModelChoiceField(
        queryset=ReasonCode.objects.all(), 
        label="Reason", 
        empty_label="Select Reason",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean_quantity(self):
        data = self.cleaned_data['quantity']
        if data <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return data
