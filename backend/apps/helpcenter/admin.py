from django.contrib import admin

from .models import HelpArticle, HelpRequest


@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_published")
    list_editable = ("order", "is_published")
    search_fields = ("question",)


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ("subject", "student", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "message", "student__school_id")
