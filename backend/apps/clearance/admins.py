from django.contrib import admin
from .models import ClearanceItem


@admin.register(ClearanceItem)
class ClearanceItemAdmin(admin.ModelAdmin):
    list_display = ("student", "office", "status", "remarks", "updated_at")
    list_filter = ("status", "office")
    search_fields = ("student__username", "office")