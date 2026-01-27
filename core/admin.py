from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, SettingGroup, SystemSetting, AuditLog
from .utils import ConfigurationManager

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom Admin configuration for the Custom User model.
    Extends the default UserAdmin to include 'role' and 'employee_code'.
    """
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'role', 
        'employee_code', 
        'is_staff'
    )
    
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'employee_code')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'employee_code')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password', 'confirm_password', 'role', 'employee_code'),
        }),
    )

class SystemSettingInline(admin.TabularInline):
    model = SystemSetting
    extra = 1
    fields = ('setting_key', 'setting_value', 'data_type', 'is_active')

@admin.register(SettingGroup)
class SettingGroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'description')
    search_fields = ('group_name',)
    inlines = [SystemSettingInline]

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('setting_key', 'setting_value', 'data_type', 'group', 'is_active', 'updated_at')
    list_filter = ('group', 'data_type', 'is_active')
    search_fields = ('setting_key', 'setting_value')
    list_editable = ('setting_value', 'is_active')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        ConfigurationManager.reload_config()

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'target_model', 'target_object_id')
    list_filter = ('action', 'timestamp', 'target_model')
    search_fields = ('target_object_id', 'changes', 'actor__username')
    readonly_fields = ('timestamp', 'actor', 'action', 'target_model', 'target_object_id', 'changes', 'ip_address')
    
    def has_add_permission(self, request):
        return False  # Audit logs should not be created manually via Admin

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should be immutable
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should not be deleted manually
