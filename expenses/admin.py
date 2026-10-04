from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'owner', 'category', 'description', 'amount')
    list_filter = ('owner', 'category', 'date')
    search_fields = ('owner__username', 'category', 'description')
