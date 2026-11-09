from django.contrib import admin

from .models import Income, Loan, Repayment


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('date', 'owner', 'source', 'amount', 'payment_mode', 'payment_app')
    list_filter = ('owner', 'source', 'date')
    search_fields = ('owner__username', 'source', 'description')


class RepaymentInline(admin.TabularInline):
    model = Repayment
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('date', 'owner', 'person', 'direction', 'amount', 'due_date')
    list_filter = ('owner', 'direction', 'date')
    search_fields = ('owner__username', 'person', 'note')
    inlines = [RepaymentInline]
