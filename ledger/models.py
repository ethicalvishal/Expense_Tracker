from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from expenses.models import Expense

ZERO = Decimal('0')
MIN_AMOUNT = [MinValueValidator(Decimal('0.01'))]


class Income(models.Model):
    """Money that came IN: salary, freelance work, a gift, a refund..."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incomes',
    )
    date = models.DateField()
    source = models.CharField(max_length=100)  # where it came from, e.g. Salary
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=MIN_AMOUNT)
    payment_mode = models.CharField(
        max_length=10, choices=Expense.PAYMENT_MODE_CHOICES, blank=True, default='',
    )
    payment_app = models.CharField(
        max_length=12, choices=Expense.PAYMENT_APP_CHOICES, blank=True, default='',
    )

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.date} - {self.source} - ₹{self.amount}"

    @property
    def payment_label(self):
        if self.payment_mode == Expense.OFFLINE:
            return 'Cash'
        if self.payment_mode == Expense.ONLINE:
            return self.get_payment_app_display() or 'Online'
        return ''


class LoanQuerySet(models.QuerySet):
    def with_balance(self):
        """Adds `repaid` (total of all repayments) to every loan in one query."""
        return self.annotate(
            repaid=Coalesce(
                Sum('repayments__amount'),
                Value(ZERO),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )


class Loan(models.Model):
    """Money lent to someone, or borrowed from someone."""

    LENT = 'lent'
    BORROWED = 'borrowed'
    DIRECTION_CHOICES = [
        (LENT, 'I lent (gave money)'),
        (BORROWED, 'I borrowed (took money)'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loans',
    )
    person = models.CharField(max_length=100)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    date = models.DateField()  # the day the money was given / taken
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=MIN_AMOUNT)
    due_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    payment_mode = models.CharField(
        max_length=10, choices=Expense.PAYMENT_MODE_CHOICES, blank=True, default='',
    )
    payment_app = models.CharField(
        max_length=12, choices=Expense.PAYMENT_APP_CHOICES, blank=True, default='',
    )

    objects = LoanQuerySet.as_manager()

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.get_direction_display()} - {self.person} - ₹{self.amount}"

    @property
    def payment_label(self):
        if self.payment_mode == Expense.OFFLINE:
            return 'Cash'
        if self.payment_mode == Expense.ONLINE:
            return self.get_payment_app_display() or 'Online'
        return ''

    @property
    def repaid_amount(self):
        if hasattr(self, 'repaid'):  # already loaded by with_balance()
            return self.repaid
        return self.repayments.aggregate(total=Sum('amount'))['total'] or ZERO

    @property
    def remaining(self):
        return self.amount - self.repaid_amount

    @property
    def repaid_percent(self):
        if not self.amount:
            return 0
        return min(100, round(float(self.repaid_amount / self.amount * 100)))

    @property
    def status(self):
        if self.remaining <= 0:
            return 'settled'
        if self.repaid_amount > 0:
            return 'partial'
        return 'pending'

    @property
    def is_overdue(self):
        return bool(self.due_date) and self.remaining > 0 and self.due_date < timezone.localdate()


class Repayment(models.Model):
    """A part (or all) of a loan coming back. A loan can have many repayments."""

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=MIN_AMOUNT)
    note = models.CharField(max_length=200, blank=True)
    payment_mode = models.CharField(
        max_length=10, choices=Expense.PAYMENT_MODE_CHOICES, blank=True, default='',
    )
    payment_app = models.CharField(
        max_length=12, choices=Expense.PAYMENT_APP_CHOICES, blank=True, default='',
    )

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.loan.person} - ₹{self.amount} on {self.date}"

    @property
    def payment_label(self):
        if self.payment_mode == Expense.OFFLINE:
            return 'Cash'
        if self.payment_mode == Expense.ONLINE:
            return self.get_payment_app_display() or 'Online'
        return ''
