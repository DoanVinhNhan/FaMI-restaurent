from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Promotion

class PromotionForm(forms.ModelForm):
    """
    Form for managing promotions.
    """
    class Meta:
        model = Promotion
        fields = [
            'name', 'promo_code', 'discount_type', 'discount_value', 
            'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'promo_code': forms.TextInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("End date cannot be before start date.")
        
        return cleaned_data

    def clean_promo_code(self):
        code = self.cleaned_data['promo_code']
        instance = getattr(self, 'instance', None)
        
        # Check uniqueness excluding self
        qs = Promotion.objects.filter(promo_code=code)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
            
        if qs.exists():
            raise ValidationError(f"Promotion code '{code}' already exists.")
            
        return code
