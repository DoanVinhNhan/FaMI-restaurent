from django import forms
from django.forms import modelformset_factory
from .models import StockTakeTicket, StockTakeDetail

class StockTakeTicketForm(forms.ModelForm):
    class Meta:
        model = StockTakeTicket
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes for this session...'}),
        }

class StockTakeDetailForm(forms.ModelForm):
    """
    Form for a single line item in the stock take.
    """
    class Meta:
        model = StockTakeDetail
        fields = ['actual_quantity', 'reason']
        widgets = {
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for variance'}),
        }

# Create a formset to edit multiple details at once
StockTakeDetailFormSet = modelformset_factory(
    StockTakeDetail,
    form=StockTakeDetailForm,
    extra=0, # No empty extra rows
    can_delete=False
)
