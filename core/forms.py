from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'role', 'employee_code', 'first_name', 'last_name')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'employee_code': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CustomUserChangeForm(UserChangeForm):
    password = None # Don't allow password change here for simplicity/security
    
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'employee_code', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'employee_code': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

from .models import SystemSetting

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ('setting_value', 'is_active')
        widgets = {
            'setting_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
