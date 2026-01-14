from django import forms
from .models import Expense

class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        widget = forms.DateInput(
            attrs = {'type': 'date', 'class': 'form-control'}
        )
    )
    
    class Meta:
        model = Expense
        fields = ['amount', 'category', 'description', 'date']