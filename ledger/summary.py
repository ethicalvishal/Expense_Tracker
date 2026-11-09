"""Totals shared by the dashboard and the loans page."""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Income, Loan

ZERO = Decimal('0')


def loan_totals(user):
    """What the user will get back, what they owe, who is overdue, and the per-person balance."""
    today = timezone.localdate()
    to_receive = to_pay = ZERO
    overdue = open_count = 0
    people = {}

    for loan in Loan.objects.filter(owner=user).with_balance():
        remaining = loan.amount - loan.repaid
        if remaining <= 0:
            continue  # settled
        open_count += 1
        signed = remaining if loan.direction == Loan.LENT else -remaining
        if loan.direction == Loan.LENT:
            to_receive += remaining
        else:
            to_pay += remaining
        if loan.due_date and loan.due_date < today:
            overdue += 1
        entry = people.setdefault(loan.person, {'name': loan.person, 'net': ZERO, 'loans': 0})
        entry['net'] += signed
        entry['loans'] += 1

    people_list = sorted(people.values(), key=lambda item: abs(item['net']), reverse=True)
    for item in people_list:
        item['net_abs'] = abs(item['net'])

    return {
        'to_receive': to_receive,
        'to_pay': to_pay,
        'overdue_count': overdue,
        'open_count': open_count,
        'people': people_list,
    }


def dashboard_summary(user, month_start, next_month):
    income = Income.objects.filter(owner=user, date__gte=month_start, date__lt=next_month)
    totals = loan_totals(user)
    return {
        'income_month': income.aggregate(total=Sum('amount'))['total'] or ZERO,
        'to_receive': totals['to_receive'],
        'to_pay': totals['to_pay'],
        'overdue_count': totals['overdue_count'],
    }
