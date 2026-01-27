from django.contrib import admin
from .models import ReasonCode, WasteReport, StatusHistory

@admin.register(ReasonCode)
class ReasonCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

@admin.register(WasteReport)
class WasteReportAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'actor', 'content_object', 'quantity', 'reason', 'reported_at')
    list_filter = ('reason', 'reported_at')
    search_fields = ('actor__username', 'reason__code')
    date_hierarchy = 'reported_at'

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('history_id', 'order_detail', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('order_detail__id', 'changed_by__username')
    date_hierarchy = 'changed_at'
