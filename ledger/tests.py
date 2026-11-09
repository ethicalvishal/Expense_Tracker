from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Income, Loan, Repayment

User = get_user_model()
PASSWORD = 'S3cure-Pass-99'


class BaseTestCase(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.alice = User.objects.create_user('alice', 'alice@example.com', PASSWORD)
        self.bob = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        self.client.force_login(self.alice)

    def make_income(self, owner, **overrides):
        data = {
            'owner': owner, 'date': self.today, 'source': 'Salary',
            'amount': Decimal('1000'), 'payment_mode': 'online', 'payment_app': 'gpay',
        }
        data.update(overrides)
        return Income.objects.create(**data)

    def make_loan(self, owner, **overrides):
        data = {
            'owner': owner, 'person': 'Rahul', 'direction': Loan.LENT, 'date': self.today,
            'amount': Decimal('1000'), 'payment_mode': 'offline',
        }
        data.update(overrides)
        return Loan.objects.create(**data)

    def make_repayment(self, loan, amount, **overrides):
        data = {'loan': loan, 'date': self.today, 'amount': Decimal(amount), 'payment_mode': 'offline'}
        data.update(overrides)
        return Repayment.objects.create(**data)

    def income_post(self, **overrides):
        data = {
            'date': '2026-01-10', 'source': 'salary', 'description': '',
            'amount': '5000', 'payment_mode': 'offline',
        }
        data.update(overrides)
        return data

    def loan_post(self, **overrides):
        data = {
            'direction': 'lent', 'person': 'rahul', 'date': '2026-01-10', 'amount': '1000',
            'due_date': '', 'note': '', 'payment_mode': 'offline',
        }
        data.update(overrides)
        return data

    def repayment_post(self, **overrides):
        data = {
            'date': '2026-01-20', 'amount': '400', 'note': '', 'payment_mode': 'offline',
        }
        data.update(overrides)
        return data


class AccessTests(BaseTestCase):
    def test_anonymous_users_are_sent_to_login(self):
        self.client.logout()
        for name in ('income_list', 'income_add', 'loan_list', 'loan_add'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response['Location'].startswith(reverse('login')), name)

    def test_pages_load(self):
        for name in ('income_list', 'income_add', 'loan_list', 'loan_add'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class IncomeTests(BaseTestCase):
    def test_add_income_is_owned_by_logged_in_user(self):
        response = self.client.post(reverse('income_add'), self.income_post())
        self.assertRedirects(response, reverse('income_list'))
        income = Income.objects.get()
        self.assertEqual(income.owner, self.alice)
        self.assertEqual(income.source, 'Salary')  # "salary" tidied up
        self.assertEqual(income.amount, Decimal('5000'))
        self.assertEqual(income.payment_label, 'Cash')

    def test_owner_cannot_be_forged(self):
        self.client.post(reverse('income_add'), self.income_post(owner=self.bob.id))
        self.assertEqual(Income.objects.get().owner, self.alice)

    def test_online_income_needs_an_app(self):
        response = self.client.post(reverse('income_add'), self.income_post(payment_mode='online'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Income.objects.count(), 0)

    def test_online_income_with_app(self):
        self.client.post(reverse('income_add'), self.income_post(payment_mode='online', payment_app='phonepe'))
        self.assertEqual(Income.objects.get().payment_label, 'PhonePe')

    def test_amount_must_be_positive_and_mode_required(self):
        for bad in ({'amount': '0'}, {'amount': '-5'}):
            self.assertEqual(self.client.post(reverse('income_add'), self.income_post(**bad)).status_code, 200)
        data = self.income_post()
        del data['payment_mode']
        self.assertEqual(self.client.post(reverse('income_add'), data).status_code, 200)
        self.assertEqual(Income.objects.count(), 0)

    def test_edit_income(self):
        income = self.make_income(self.alice)
        self.client.post(reverse('income_edit', args=[income.id]), self.income_post(source='gift', amount='250'))
        income.refresh_from_db()
        self.assertEqual((income.source, income.amount), ('Gift', Decimal('250')))

    def test_other_users_income_is_hidden_and_protected(self):
        bobs = self.make_income(self.bob, description='Bob secret')
        self.assertNotContains(self.client.get(reverse('income_list')), 'Bob secret')
        self.assertEqual(self.client.get(reverse('income_edit', args=[bobs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('income_delete', args=[bobs.id])).status_code, 404)
        self.assertEqual(Income.objects.count(), 1)

    def test_delete_requires_post(self):
        income = self.make_income(self.alice)
        url = reverse('income_delete', args=[income.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual(Income.objects.count(), 0)

    def test_totals_split_and_filters(self):
        self.make_income(self.alice, source='Salary', amount=Decimal('3000'), payment_mode='online', payment_app='gpay')
        self.make_income(self.alice, source='Gift', amount=Decimal('500'), payment_mode='offline', payment_app='')
        self.make_income(self.bob, amount=Decimal('999'))
        response = self.client.get(reverse('income_list'))
        self.assertEqual(response.context['result_total'], Decimal('3500'))
        self.assertEqual(response.context['split']['online'], Decimal('3000'))
        self.assertEqual(response.context['split']['offline'], Decimal('500'))
        self.assertEqual(self.client.get(reverse('income_list'), {'q': 'gift'}).context['result_count'], 1)


class LoanTests(BaseTestCase):
    def test_add_loan(self):
        response = self.client.post(reverse('loan_add'), self.loan_post())
        loan = Loan.objects.get()
        self.assertRedirects(response, reverse('loan_detail', args=[loan.id]))
        self.assertEqual((loan.owner, loan.person, loan.direction), (self.alice, 'Rahul', 'lent'))
        self.assertEqual(loan.status, 'pending')

    def test_return_date_cannot_be_before_the_loan_date(self):
        response = self.client.post(reverse('loan_add'), self.loan_post(due_date='2026-01-01'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Loan.objects.count(), 0)

    def test_loan_needs_a_direction_and_positive_amount(self):
        data = self.loan_post()
        del data['direction']
        self.assertEqual(self.client.post(reverse('loan_add'), data).status_code, 200)
        self.assertEqual(self.client.post(reverse('loan_add'), self.loan_post(amount='0')).status_code, 200)
        self.assertEqual(Loan.objects.count(), 0)

    def test_partial_then_full_repayment(self):
        loan = self.make_loan(self.alice)
        url = reverse('loan_detail', args=[loan.id])

        self.client.post(url, self.repayment_post(amount='250'))
        loan = Loan.objects.get(pk=loan.pk)
        self.assertEqual(loan.remaining, Decimal('750'))
        self.assertEqual(loan.status, 'partial')
        self.assertEqual(loan.repaid_percent, 25)

        self.client.post(url, self.repayment_post(amount='750'))
        loan = Loan.objects.get(pk=loan.pk)
        self.assertEqual(loan.remaining, Decimal('0'))
        self.assertEqual(loan.status, 'settled')
        self.assertEqual(loan.repayments.count(), 2)

    def test_repayment_cannot_exceed_what_is_pending(self):
        loan = self.make_loan(self.alice)
        self.make_repayment(loan, '600')
        response = self.client.post(reverse('loan_detail', args=[loan.id]), self.repayment_post(amount='500'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(loan.repayments.count(), 1)

    def test_repayment_needs_payment_mode_and_app_when_online(self):
        loan = self.make_loan(self.alice)
        url = reverse('loan_detail', args=[loan.id])
        self.client.post(url, self.repayment_post(payment_mode='online'))
        self.assertEqual(loan.repayments.count(), 0)
        self.client.post(url, self.repayment_post(payment_mode='online', payment_app='navi'))
        self.assertEqual(loan.repayments.get().payment_label, 'Navi')

    def test_no_repayment_on_a_settled_loan(self):
        loan = self.make_loan(self.alice, amount=Decimal('100'))
        self.make_repayment(loan, '100')
        self.client.post(reverse('loan_detail', args=[loan.id]), self.repayment_post(amount='1'))
        self.assertEqual(loan.repayments.count(), 1)

    def test_delete_repayment_brings_the_pending_amount_back(self):
        loan = self.make_loan(self.alice)
        repayment = self.make_repayment(loan, '400')
        url = reverse('repayment_delete', args=[repayment.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual(Loan.objects.get(pk=loan.pk).remaining, Decimal('1000'))

    def test_other_users_loans_are_protected(self):
        bobs = self.make_loan(self.bob, person='Bobs Friend')
        repayment = self.make_repayment(bobs, '10')
        self.assertNotContains(self.client.get(reverse('loan_list')), 'Bobs Friend')
        self.assertEqual(self.client.get(reverse('loan_detail', args=[bobs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('loan_detail', args=[bobs.id]), self.repayment_post()).status_code, 404)
        self.assertEqual(self.client.get(reverse('loan_edit', args=[bobs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('loan_delete', args=[bobs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('repayment_delete', args=[repayment.id])).status_code, 404)
        self.assertEqual((Loan.objects.count(), Repayment.objects.count()), (1, 1))

    def test_loan_list_is_ordered_newest_first_across_pages(self):
        for i in range(12):
            self.make_loan(self.alice, person=f'Person{i}', date=self.today - timedelta(days=i))
        page1 = self.client.get(reverse('loan_list')).context['page_obj']
        dates = [loan.date for loan in page1]
        self.assertEqual(dates, sorted(dates, reverse=True))
        page2 = self.client.get(reverse('loan_list'), {'page': 2}).context['page_obj']
        self.assertEqual([loan.person for loan in page2], ['Person10', 'Person11'])

    def test_edit_loan_cannot_go_below_what_was_repaid(self):
        loan = self.make_loan(self.alice)
        self.make_repayment(loan, '400')
        url = reverse('loan_edit', args=[loan.id])
        self.assertEqual(self.client.post(url, self.loan_post(amount='300')).status_code, 200)
        self.assertEqual(Loan.objects.get(pk=loan.pk).amount, Decimal('1000'))
        self.client.post(url, self.loan_post(amount='500', person='mohan'))
        loan.refresh_from_db()
        self.assertEqual((loan.amount, loan.person), (Decimal('500'), 'Mohan'))

    def test_delete_loan_removes_its_repayments(self):
        loan = self.make_loan(self.alice)
        self.make_repayment(loan, '400')
        url = reverse('loan_delete', args=[loan.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual((Loan.objects.count(), Repayment.objects.count()), (0, 0))


class LoanListTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.rahul = self.make_loan(self.alice, person='Rahul', amount=Decimal('1000'))
        self.make_repayment(self.rahul, '400')
        self.make_loan(self.alice, person='Rahul', direction=Loan.BORROWED, amount=Decimal('100'))
        self.make_loan(self.alice, person='Sita', direction=Loan.BORROWED, amount=Decimal('300'))
        done = self.make_loan(self.alice, person='Amit', amount=Decimal('50'))
        self.make_repayment(done, '50')
        self.make_loan(self.bob, person='Bob Only', amount=Decimal('9999'))

    def get_list(self, **params):
        return self.client.get(reverse('loan_list'), params)

    def test_totals_ignore_settled_loans_and_other_users(self):
        totals = self.get_list().context['totals']
        self.assertEqual(totals['to_receive'], Decimal('600'))
        self.assertEqual(totals['to_pay'], Decimal('400'))
        self.assertEqual(totals['open_count'], 3)

    def test_balance_per_person(self):
        people = {p['name']: p['net'] for p in self.get_list().context['totals']['people']}
        self.assertEqual(people, {'Rahul': Decimal('500'), 'Sita': Decimal('-300')})

    def test_filters(self):
        self.assertEqual(self.get_list().context['result_count'], 4)
        self.assertEqual(self.get_list(direction='borrowed').context['result_count'], 2)
        self.assertEqual(self.get_list(status='settled').context['result_count'], 1)
        self.assertEqual(self.get_list(status='open').context['result_count'], 3)
        self.assertEqual(self.get_list(q='sit').context['result_count'], 1)

    def test_overdue_only_counts_open_loans(self):
        yesterday = self.today - timedelta(days=1)
        Loan.objects.filter(pk=self.rahul.pk).update(due_date=yesterday)
        settled = Loan.objects.get(person='Amit')
        Loan.objects.filter(pk=settled.pk).update(due_date=yesterday)
        self.assertEqual(self.get_list().context['totals']['overdue_count'], 1)
        self.assertTrue(Loan.objects.get(pk=self.rahul.pk).is_overdue)
        self.assertFalse(Loan.objects.get(pk=settled.pk).is_overdue)


class DashboardMoneyTests(BaseTestCase):
    def test_dashboard_shows_income_balance_and_loans(self):
        from expenses.models import Expense
        self.make_income(self.alice, amount=Decimal('5000'))
        self.make_income(self.bob, amount=Decimal('777'))
        Expense.objects.create(owner=self.alice, date=self.today, category='Food', amount=Decimal('1200'))
        lent = self.make_loan(self.alice, amount=Decimal('1000'))
        self.make_repayment(lent, '250')
        self.make_loan(self.alice, direction=Loan.BORROWED, person='Sita', amount=Decimal('300'),
                       due_date=self.today - timedelta(days=2))

        context = self.client.get(reverse('dashboard')).context
        self.assertEqual(context['income_month'], Decimal('5000'))
        self.assertEqual(context['balance'], Decimal('3800'))
        self.assertEqual(context['to_receive'], Decimal('750'))
        self.assertEqual(context['to_pay'], Decimal('300'))
        self.assertEqual(context['overdue_loans'], 1)

    def test_negative_balance_still_renders(self):
        from expenses.models import Expense
        Expense.objects.create(owner=self.alice, date=self.today, category='Food', amount=Decimal('100'))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['balance'], Decimal('-100'))
        self.assertContains(response, '-₹100.00')
