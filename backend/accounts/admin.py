
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_active',
    )

    list_filter = ('role', 'is_active')

    fieldsets = UserAdmin.fieldsets + (
        ('CTU-G Information', {
            'fields': (
                'role',
                'student_id',
                'course',
                'year_level',
                'section',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('CTU-G Information', {
            'fields': (
                'role',
                'student_id',
                'course',
                'year_level',
                'section',
            )
        }),
    )
