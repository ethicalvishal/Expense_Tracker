from django.shortcuts import render, redirect
from .models import Expense
from .forms import ExpenseForm

# Create your views here.
def expense_list(request):
    form = ExpenseForm()
    expenses = Expense.objects.all()
    total_amount = sum(e.amount for e in expenses)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    return render(request, 'expenses/index.html',{
        'form': form,
        'expenses': expenses,
        'total_amount': total_amount
    })