from django.urls import path

from . import views

urlpatterns = [
    # Income
    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.income_add, name='income_add'),
    path('income/<int:income_id>/edit/', views.income_edit, name='income_edit'),
    path('income/<int:income_id>/delete/', views.income_delete, name='income_delete'),

    # Loans (money lent to / borrowed from people) and their repayments
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/add/', views.loan_add, name='loan_add'),
    path('loans/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:loan_id>/edit/', views.loan_edit, name='loan_edit'),
    path('loans/<int:loan_id>/delete/', views.loan_delete, name='loan_delete'),
    path('loans/repayments/<int:repayment_id>/delete/', views.repayment_delete, name='repayment_delete'),
]
