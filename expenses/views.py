from django.shortcuts import render, redirect, get_object_or_404
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
    
    # Delete Single Expense
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    return redirect('/')

# Delete All Expenses
def delete_all_expenses(request):
    Expense.objects.all().delete()
    return redirect('/')