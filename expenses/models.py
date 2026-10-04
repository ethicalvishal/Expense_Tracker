from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
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

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['owner', 'date'], name='expense_owner_date_idx'),
        ]

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
