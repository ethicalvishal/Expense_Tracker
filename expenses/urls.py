from django.urls import path
from .views import expense_list, delete_expense, delete_all_expenses

urlpatterns = [
    path('', expense_list),
    path('delete/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('delete_all/', delete_all_expenses, name='delete_all_expenses'),
]