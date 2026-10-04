from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import (
    LoginForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)

FORM_PAGE = 'expenses/auth_form.html'
MESSAGE_PAGE = 'expenses/message_page.html'

urlpatterns = [
    # Dashboard & expenses
    path('', views.dashboard, name='dashboard'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/export/', views.export_csv, name='export_csv'),
    path('expenses/<int:expense_id>/edit/', views.edit_expense, name='edit_expense'),
    path('delete/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('delete_all/', views.delete_all_expenses, name='delete_all_expenses'),

    # Budget
    path('budget/', views.budget, name='budget'),
    path('budget/remove/', views.remove_budget, name='remove_budget'),

    # Accounts
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(
        template_name='expenses/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # POST only
    path('account/', views.account, name='account'),
    path('account/delete/', views.delete_account, name='delete_account'),

    # Change password (logged in)
    path('password/change/', auth_views.PasswordChangeView.as_view(
        template_name=FORM_PAGE,
        form_class=StyledPasswordChangeForm,
        success_url=reverse_lazy('password_change_done'),
        extra_context={'submit_label': 'Update password'},
    ), name='password_change'),
    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name=MESSAGE_PAGE,
        extra_context={'message': 'Your password was changed successfully.'},
    ), name='password_change_done'),

    # Forgot password (by email)
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name=FORM_PAGE,
        form_class=StyledPasswordResetForm,
        email_template_name='expenses/password_reset_email.txt',
        subject_template_name='expenses/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
        extra_context={'submit_label': 'Send reset link'},
    ), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name=MESSAGE_PAGE,
        extra_context={
            'message': 'If an account with that email exists, we have sent a reset link. '
                       'Check your inbox (and spam folder).',
        },
    ), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name=FORM_PAGE,
        form_class=StyledSetPasswordForm,
        success_url=reverse_lazy('password_reset_complete'),
        extra_context={'submit_label': 'Set new password'},
    ), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name=MESSAGE_PAGE,
        extra_context={'message': 'Your password has been set. You can log in now.'},
    ), name='password_reset_complete'),

    # Health check
    path('healthz/', views.healthz, name='healthz'),
]
