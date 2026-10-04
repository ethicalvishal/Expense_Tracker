import csv
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CATEGORY_SUGGESTIONS,
    AccountForm,
    BudgetForm,
    ExpenseFilterForm,
    ExpenseForm,
    SignUpForm,
)
from .models import Budget, Expense

User = get_user_model()
ZERO = Decimal('0')


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _shift_month(d, delta):
    """First day of the month that is `delta` months away from d's month."""
    index = d.year * 12 + (d.month - 1) + delta
    return date(index // 12, index % 12 + 1, 1)


def _sum(queryset):
    return queryset.aggregate(total=Sum('amount'))['total'] or ZERO


def _filtered_expenses(request):
    """The logged-in user's expenses, narrowed by the search/filter box."""
    queryset = Expense.objects.filter(owner=request.user)
    form = ExpenseFilterForm(request.GET or None, user=request.user)
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        if data['q']:
            queryset = queryset.filter(
                Q(category__icontains=data['q']) | Q(description__icontains=data['q'])
            )
        if data['category']:
            queryset = queryset.filter(category=data['category'])
        if data['start']:
            queryset = queryset.filter(date__gte=data['start'])
        if data['end']:
            queryset = queryset.filter(date__lte=data['end'])
    return queryset, form


def _csv_safe(value):
    """Stop spreadsheet apps from running user text as a formula."""
    value = str(value)
    if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

def signup(request):
    """Create a new account and log the user straight in."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account is ready.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'expenses/signup.html', {'form': form})


@login_required
def account(request):
    # Use a fresh copy so a failed form never changes request.user in memory.
    user = User.objects.get(pk=request.user.pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('account')
    else:
        form = AccountForm(instance=user)
    return render(request, 'expenses/account.html', {
        'form': form,
        'expense_count': Expense.objects.filter(owner=user).count(),
    })


@login_required
@require_POST
def delete_account(request):
    """Permanently delete the account and all its expenses (password required)."""
    if not request.user.check_password(request.POST.get('password', '')):
        messages.error(request, 'Wrong password - your account was NOT deleted.')
        return redirect('account')
    user_id = request.user.pk
    logout(request)
    User.objects.filter(pk=user_id).delete()  # expenses + budget cascade
    messages.success(request, 'Your account and all your data have been deleted.')
    return redirect('login')


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@login_required
def dashboard(request):
    expenses = Expense.objects.filter(owner=request.user)
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month = _shift_month(month_start, 1)

    month_expenses = expenses.filter(date__gte=month_start, date__lt=next_month)
    month_total = _sum(month_expenses)

    # Spending by category this month.
    by_category = list(
        month_expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    )

    # Last 6 months trend (months with no spending show as 0).
    trend_rows = (
        expenses.filter(date__gte=_shift_month(month_start, -5), date__lt=next_month)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    trend_totals = {(row['month'].year, row['month'].month): row['total'] for row in trend_rows}
    trend_labels, trend_values = [], []
    for back in range(5, -1, -1):
        month = _shift_month(month_start, -back)
        trend_labels.append(month.strftime('%b %Y'))
        trend_values.append(float(trend_totals.get((month.year, month.month), ZERO)))

    # Budget progress.
    budget = Budget.objects.filter(owner=request.user).first()
    budget_info = None
    if budget:
        percent = float(month_total / budget.monthly_limit * 100)
        budget_info = {
            'limit': budget.monthly_limit,
            'remaining': budget.monthly_limit - month_total,
            'over_by': month_total - budget.monthly_limit,
            'over': month_total > budget.monthly_limit,
            'percent': min(100, round(percent)),
            'level': 'danger' if percent >= 100 else 'warning' if percent >= 80 else 'success',
        }

    return render(request, 'expenses/dashboard.html', {
        'month_label': today.strftime('%B %Y'),
        'month_total': month_total,
        'all_total': _sum(expenses),
        'entry_count': expenses.count(),
        'budget': budget_info,
        'recent': expenses[:5],
        'has_category_data': bool(by_category),
        'chart_data': {
            'category': {
                'labels': [row['category'] for row in by_category],
                'values': [float(row['total']) for row in by_category],
            },
            'trend': {'labels': trend_labels, 'values': trend_values},
        },
    })


# --------------------------------------------------------------------------
# Expenses
# --------------------------------------------------------------------------

@login_required
def expense_list(request):
    queryset, filter_form = _filtered_expenses(request)
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'expenses/expense_list.html', {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'result_count': paginator.count,
        'result_total': _sum(queryset),
        'query_string': params.urlencode(),
        'has_filters': bool(params),
    })


def _expense_form_page(request, form, title, submit_label):
    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'title': title,
        'submit_label': submit_label,
        'category_suggestions': CATEGORY_SUGGESTIONS,
    })


@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.owner = request.user  # always the logged-in user
            expense.save()
            messages.success(request, 'Expense added.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(initial={'date': timezone.localdate()})
    return _expense_form_page(request, form, 'Add expense', 'Add Expense')


@login_required
def edit_expense(request, expense_id):
    # owner=request.user: someone else's expense gives a 404.
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return _expense_form_page(request, form, 'Edit expense', 'Save Changes')


@login_required
@require_POST
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    expense.delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


@login_required
@require_POST
def delete_all_expenses(request):
    """Delete all of the logged-in user's expenses - never other users' data."""
    deleted, _ = Expense.objects.filter(owner=request.user).delete()
    messages.success(request, f'Deleted {deleted} expense(s).')
    return redirect('expense_list')


@login_required
def export_csv(request):
    """Download the (filtered) expenses as a CSV file that opens in Excel."""
    queryset, _ = _filtered_expenses(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    response.write('\ufeff')  # BOM so Excel reads UTF-8 correctly
    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Description', 'Amount (INR)'])
    for expense in queryset:
        writer.writerow([
            expense.date.isoformat(),
            _csv_safe(expense.category),
            _csv_safe(expense.description),
            expense.amount,
        ])
    return response


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------

@login_required
def budget(request):
    instance = Budget.objects.filter(owner=request.user).first()
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            messages.success(request, 'Monthly budget saved.')
            return redirect('dashboard')
    else:
        form = BudgetForm(instance=instance)
    return render(request, 'expenses/budget.html', {'form': form, 'has_budget': instance is not None})


@login_required
@require_POST
def remove_budget(request):
    Budget.objects.filter(owner=request.user).delete()
    messages.success(request, 'Monthly budget removed.')
    return redirect('dashboard')


# --------------------------------------------------------------------------
# Health check (for Render)
# --------------------------------------------------------------------------

def healthz(request):
    return HttpResponse('ok', content_type='text/plain')
