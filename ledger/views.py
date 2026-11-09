from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from expenses.models import Expense

from .forms import (
    INCOME_SOURCES,
    IncomeFilterForm,
    IncomeForm,
    LoanFilterForm,
    LoanForm,
    RepaymentForm,
)
from .models import Income, Loan, Repayment
from .summary import loan_totals

ZERO = Decimal('0')


def _sum(queryset):
    return queryset.aggregate(total=Sum('amount'))['total'] or ZERO


# --------------------------------------------------------------------------
# Income
# --------------------------------------------------------------------------

@login_required
def income_list(request):
    queryset = Income.objects.filter(owner=request.user)
    form = IncomeFilterForm(request.GET or None)
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        if data['q']:
            queryset = queryset.filter(Q(source__icontains=data['q']) | Q(description__icontains=data['q']))
        if data['start']:
            queryset = queryset.filter(date__gte=data['start'])
        if data['end']:
            queryset = queryset.filter(date__lte=data['end'])

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    split = queryset.aggregate(
        online=Sum('amount', filter=Q(payment_mode=Expense.ONLINE)),
        offline=Sum('amount', filter=Q(payment_mode=Expense.OFFLINE)),
        unset=Sum('amount', filter=Q(payment_mode='')),
    )
    return render(request, 'ledger/income_list.html', {
        'filter_form': form,
        'page_obj': page_obj,
        'result_count': paginator.count,
        'result_total': _sum(queryset),
        'split': {key: value or ZERO for key, value in split.items()},
        'query_string': params.urlencode(),
        'has_filters': bool(params),
    })


def _income_form_page(request, form, title, submit_label):
    return render(request, 'ledger/income_form.html', {
        'form': form,
        'title': title,
        'submit_label': submit_label,
        'source_suggestions': INCOME_SOURCES,
    })


@login_required
def income_add(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.owner = request.user  # always the logged-in user
            income.save()
            messages.success(request, 'Income added.')
            return redirect('income_list')
    else:
        form = IncomeForm(initial={'date': timezone.localdate(), 'payment_mode': Expense.ONLINE})
    return _income_form_page(request, form, 'Add income', 'Add Income')


@login_required
def income_edit(request, income_id):
    income = get_object_or_404(Income, id=income_id, owner=request.user)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, 'Income updated.')
            return redirect('income_list')
    else:
        form = IncomeForm(instance=income)
    return _income_form_page(request, form, 'Edit income', 'Save Changes')


@login_required
@require_POST
def income_delete(request, income_id):
    get_object_or_404(Income, id=income_id, owner=request.user).delete()
    messages.success(request, 'Income deleted.')
    return redirect('income_list')


# --------------------------------------------------------------------------
# Loans
# --------------------------------------------------------------------------

@login_required
def loan_list(request):
    totals = loan_totals(request.user)

    # Explicit order: annotated (grouped) queries ignore the model's default ordering,
    # and the pages need a stable order.
    loans = Loan.objects.filter(owner=request.user).with_balance().order_by('-date', '-id')
    form = LoanFilterForm(request.GET or None)
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        if data['q']:
            loans = loans.filter(person__icontains=data['q'])
        if data['direction']:
            loans = loans.filter(direction=data['direction'])
        if data['status'] == 'open':
            loans = loans.filter(amount__gt=F('repaid'))
        elif data['status'] == 'settled':
            loans = loans.filter(amount__lte=F('repaid'))

    paginator = Paginator(loans, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'ledger/loan_list.html', {
        'filter_form': form,
        'page_obj': page_obj,
        'result_count': paginator.count,
        'totals': totals,
        'query_string': params.urlencode(),
        'has_filters': bool(params),
    })


def _loan_form_page(request, form, title, submit_label):
    return render(request, 'ledger/loan_form.html', {
        'form': form,
        'title': title,
        'submit_label': submit_label,
    })


@login_required
def loan_add(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.owner = request.user
            loan.save()
            messages.success(request, 'Loan saved.')
            return redirect('loan_detail', loan_id=loan.id)
    else:
        form = LoanForm(initial={
            'date': timezone.localdate(),
            'direction': Loan.LENT,
            'payment_mode': Expense.ONLINE,
        })
    return _loan_form_page(request, form, 'Add loan', 'Save Loan')


@login_required
def loan_edit(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, owner=request.user)
    if request.method == 'POST':
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, 'Loan updated.')
            return redirect('loan_detail', loan_id=loan.id)
    else:
        form = LoanForm(instance=loan)
    return _loan_form_page(request, form, 'Edit loan', 'Save Changes')


@login_required
@require_POST
def loan_delete(request, loan_id):
    get_object_or_404(Loan, id=loan_id, owner=request.user).delete()  # repayments go with it
    messages.success(request, 'Loan deleted.')
    return redirect('loan_list')


@login_required
def loan_detail(request, loan_id):
    """One loan with its repayments, plus the form to record a new repayment."""
    loan = get_object_or_404(Loan.objects.filter(owner=request.user).with_balance(), id=loan_id)

    if request.method == 'POST':
        if loan.remaining <= 0:
            messages.error(request, 'This loan is already fully repaid.')
            return redirect('loan_detail', loan_id=loan.id)
        form = RepaymentForm(request.POST, loan=loan)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.loan = loan
            repayment.save()
            messages.success(request, 'Repayment recorded.')
            return redirect('loan_detail', loan_id=loan.id)
    else:
        form = RepaymentForm(loan=loan, initial={
            'date': timezone.localdate(),
            'amount': loan.remaining if loan.remaining > 0 else None,
            'payment_mode': Expense.ONLINE,
        })

    return render(request, 'ledger/loan_detail.html', {
        'loan': loan,
        'repayments': loan.repayments.all(),
        'form': form,
    })


@login_required
@require_POST
def repayment_delete(request, repayment_id):
    repayment = get_object_or_404(Repayment, id=repayment_id, loan__owner=request.user)
    loan_id = repayment.loan_id
    repayment.delete()
    messages.success(request, 'Repayment removed.')
    return redirect('loan_detail', loan_id=loan_id)
