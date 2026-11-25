from django.contrib import admin
from .models import Assessment, Payment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("student", "semester", "total")
    list_filter = ("semester",)
    search_fields = ("student__school_id", "semester")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "student", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "student__school_id")
