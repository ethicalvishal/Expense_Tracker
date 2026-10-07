from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
    # How the expense was paid: physically (cash) or online (UPI app, card, bank...).
    OFFLINE = 'offline'
    ONLINE = 'online'
    PAYMENT_MODE_CHOICES = [
        (OFFLINE, 'Offline (Cash)'),
        (ONLINE, 'Online'),
    ]
    # Which app / method was used when the payment was online.
    PAYMENT_APP_CHOICES = [
        ('gpay', 'Google Pay'),
        ('phonepe', 'PhonePe'),
        ('paytm', 'Paytm'),
        ('bhim', 'BHIM'),
        ('navi', 'Navi'),
        ('yono', 'YONO SBI'),
        ('amazonpay', 'Amazon Pay'),
        ('card', 'Debit / Credit Card'),
        ('upi', 'UPI (other app)'),
        ('bank', 'Net Banking / Bank Transfer'),
        ('other', 'Other'),
    ]

    # Who this expense belongs to. Nullable only so that rows created before
    # user accounts existed can still be migrated; they can be assigned to a
    # user in the admin panel.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
        null=True,
        blank=True,
    )
    date = models.DateField()
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    # Blank only for expenses saved before this feature existed.
    payment_mode = models.CharField(
        max_length=10, choices=PAYMENT_MODE_CHOICES, blank=True, default='',
    )
    payment_app = models.CharField(
        max_length=12, choices=PAYMENT_APP_CHOICES, blank=True, default='',
    )

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['owner', 'date'], name='expense_owner_date_idx'),
        ]

    @property
    def payment_label(self):
        """Short text for lists: 'Cash', 'Google Pay', 'Online' or '' (old rows)."""
        if self.payment_mode == self.OFFLINE:
            return 'Cash'
        if self.payment_mode == self.ONLINE:
            return self.get_payment_app_display() or 'Online'
        return ''

    def __str__(self):
        return f"{self.date} - {self.category} - {self.description} - ₹{self.amount}"


class Budget(models.Model):
    """Optional monthly spending limit, one per user."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budget',
    )
    monthly_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    def __str__(self):
        return f"{self.owner} - ₹{self.monthly_limit}/month"
