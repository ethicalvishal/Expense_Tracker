from django.db import models

# Create your models here.
class Expense(models.Model):
    date = models.DateField()
    category = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.date} - {self.category} - {self.description} - ₹{self.amount}"