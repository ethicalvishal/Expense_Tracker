import re
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Budget, Expense

User = get_user_model()
PASSWORD = 'S3cure-Pass-99'


class BaseTestCase(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', 'alice@example.com', PASSWORD)
        self.bob = User.objects.create_user('bob', 'bob@example.com', PASSWORD)

    def make_expense(self, owner, **overrides):
        data = {
            'owner': owner,
            'date': timezone.localdate(),
            'category': 'Food',
            'description': 'Lunch',
            'amount': Decimal('100.00'),
        }
        data.update(overrides)
        return Expense.objects.create(**data)

    def post_data(self, **overrides):
        data = {
            'date': '2026-01-10',
            'category': 'food',
            'description': 'Lunch',
            'amount': '120.50',
            'payment_mode': 'offline',
        }
        data.update(overrides)
        return data


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

class AuthTests(BaseTestCase):
    def test_anonymous_user_is_sent_to_login(self):
        for name in ('dashboard', 'expense_list', 'add_expense', 'budget', 'account', 'export_csv'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response['Location'].startswith(reverse('login')), name)

    def test_anonymous_user_cannot_post_or_delete(self):
        expense = self.make_expense(self.alice)
        self.client.post(reverse('add_expense'), self.post_data())
        self.client.post(reverse('delete_expense', args=[expense.id]))
        self.client.post(reverse('delete_all_expenses'))
        self.assertEqual(Expense.objects.count(), 1)

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse('signup'), {
            'username': 'carol',
            'email': 'carol@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='carol', email='carol@example.com').exists())

    def test_signup_requires_email(self):
        response = self.client.post(reverse('signup'), {
            'username': 'carol', 'email': '',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='carol').exists())

    def test_signup_rejects_duplicate_email(self):
        response = self.client.post(reverse('signup'), {
            'username': 'carol', 'email': 'ALICE@example.com',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='carol').exists())

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('signup'), {
            'username': 'carol', 'email': 'carol@example.com',
            'password1': PASSWORD, 'password2': 'something-else-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='carol').exists())

    def test_login_and_logout(self):
        response = self.client.post(reverse('login'), {'username': 'alice', 'password': PASSWORD})
        self.assertRedirects(response, reverse('dashboard'))
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('login'), {'username': 'alice', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_data_is_still_there_after_logging_in_again(self):
        self.client.force_login(self.alice)
        self.client.post(reverse('add_expense'), self.post_data())
        self.client.post(reverse('logout'))
        self.client.post(reverse('login'), {'username': 'alice', 'password': PASSWORD})
        response = self.client.get(reverse('expense_list'))
        self.assertEqual(response.context['result_count'], 1)


class PasswordTests(BaseTestCase):
    def test_password_reset_sends_email_with_working_link(self):
        response = self.client.post(reverse('password_reset'), {'email': 'alice@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r'https?://testserver(/password/reset/\S+)', mail.outbox[0].body).group(1)
        # Django swaps the token for "set-password" on the first visit.
        response = self.client.get(link, follow=True)
        self.assertEqual(response.status_code, 200)
        set_url = response.redirect_chain[-1][0]
        response = self.client.post(set_url, {
            'new_password1': 'Brand-New-Pass-77',
            'new_password2': 'Brand-New-Pass-77',
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='alice', password='Brand-New-Pass-77'))

    def test_password_reset_for_unknown_email_sends_nothing(self):
        response = self.client.post(reverse('password_reset'), {'email': 'nobody@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_change_password(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse('password_change'), {
            'old_password': PASSWORD,
            'new_password1': 'Another-Pass-55',
            'new_password2': 'Another-Pass-55',
        })
        self.assertRedirects(response, reverse('password_change_done'))
        self.assertTrue(User.objects.get(username='alice').check_password('Another-Pass-55'))


class AccountTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def test_update_profile(self):
        response = self.client.post(reverse('account'), {'first_name': 'Alice', 'email': 'new@example.com'})
        self.assertRedirects(response, reverse('account'))
        user = User.objects.get(username='alice')
        self.assertEqual((user.first_name, user.email), ('Alice', 'new@example.com'))

    def test_cannot_use_another_users_email(self):
        response = self.client.post(reverse('account'), {'first_name': 'A', 'email': 'bob@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(username='alice').email, 'alice@example.com')

    def test_delete_account_needs_correct_password(self):
        self.make_expense(self.alice)
        self.client.post(reverse('delete_account'), {'password': 'wrong'})
        self.assertTrue(User.objects.filter(username='alice').exists())
        self.assertEqual(Expense.objects.count(), 1)

    def test_delete_account_removes_only_that_users_data(self):
        self.make_expense(self.alice)
        self.make_expense(self.bob)
        self.client.post(reverse('delete_account'), {'password': PASSWORD})
        self.assertFalse(User.objects.filter(username='alice').exists())
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(Expense.objects.get().owner, self.bob)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)  # logged out


# --------------------------------------------------------------------------
# Expenses
# --------------------------------------------------------------------------

class ExpenseTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def test_pages_load(self):
        for name in ('dashboard', 'expense_list', 'add_expense', 'budget', 'account'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_add_expense_is_owned_by_logged_in_user(self):
        response = self.client.post(reverse('add_expense'), self.post_data())
        self.assertRedirects(response, reverse('expense_list'))
        expense = Expense.objects.get()
        self.assertEqual(expense.owner, self.alice)
        self.assertEqual(expense.category, 'Food')
        self.assertEqual(expense.amount, Decimal('120.50'))

    def test_owner_cannot_be_forged_through_the_form(self):
        self.client.post(reverse('add_expense'), self.post_data(owner=self.bob.id))
        self.assertEqual(Expense.objects.get().owner, self.alice)

    def test_description_is_optional(self):
        self.client.post(reverse('add_expense'), self.post_data(description=''))
        self.assertEqual(Expense.objects.count(), 1)

    def test_rejects_zero_and_negative_amount(self):
        for bad in ('0', '-5'):
            response = self.client.post(reverse('add_expense'), self.post_data(amount=bad))
            self.assertEqual(response.status_code, 200)  # form re-shown with errors
        self.assertEqual(Expense.objects.count(), 0)

    def test_edit_expense(self):
        expense = self.make_expense(self.alice)
        response = self.client.post(
            reverse('edit_expense', args=[expense.id]),
            self.post_data(category='travel', amount='55.00'),
        )
        self.assertRedirects(response, reverse('expense_list'))
        expense.refresh_from_db()
        self.assertEqual((expense.category, expense.amount, expense.owner), ('Travel', Decimal('55.00'), self.alice))

    def test_cannot_edit_another_users_expense(self):
        bobs = self.make_expense(self.bob)
        url = reverse('edit_expense', args=[bobs.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.post_data()).status_code, 404)

    def test_user_only_sees_own_expenses_and_total(self):
        self.make_expense(self.alice, amount=Decimal('10.50'))
        self.make_expense(self.alice, amount=Decimal('4.50'))
        self.make_expense(self.bob, amount=Decimal('999.00'), description='Bob secret')
        response = self.client.get(reverse('expense_list'))
        self.assertEqual(response.context['result_count'], 2)
        self.assertEqual(response.context['result_total'], Decimal('15.00'))
        self.assertNotContains(response, 'Bob secret')

    def test_delete_requires_post(self):
        expense = self.make_expense(self.alice)
        url = reverse('delete_expense', args=[expense.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Expense.objects.count(), 1)
        self.client.post(url)
        self.assertEqual(Expense.objects.count(), 0)

    def test_cannot_delete_another_users_expense(self):
        bobs = self.make_expense(self.bob)
        response = self.client.post(reverse('delete_expense', args=[bobs.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Expense.objects.count(), 1)

    def test_delete_all_only_removes_own_expenses(self):
        self.make_expense(self.alice)
        self.make_expense(self.alice)
        self.make_expense(self.bob)
        url = reverse('delete_all_expenses')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Expense.objects.count(), 3)
        self.client.post(url)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(Expense.objects.get().owner, self.bob)


class FilterAndExportTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)
        self.make_expense(self.alice, category='Food', description='Pizza', date=date(2026, 1, 5), amount=Decimal('200'))
        self.make_expense(self.alice, category='Travel', description='Bus ticket', date=date(2026, 2, 5), amount=Decimal('50'))
        self.make_expense(self.bob, category='Food', description='Bob pizza', date=date(2026, 1, 5), amount=Decimal('999'))

    def get_list(self, **params):
        return self.client.get(reverse('expense_list'), params)

    def test_search_text(self):
        response = self.get_list(q='pizza')
        self.assertEqual(response.context['result_count'], 1)

    def test_filter_by_category(self):
        response = self.get_list(category='Travel')
        self.assertEqual(response.context['result_total'], Decimal('50'))

    def test_filter_by_date_range(self):
        response = self.get_list(start='2026-02-01', end='2026-02-28')
        self.assertEqual(response.context['result_count'], 1)

    def test_pagination(self):
        for i in range(12):
            self.make_expense(self.alice, description=f'bulk {i}')
        response = self.get_list()
        self.assertEqual(response.context['result_count'], 14)
        self.assertEqual(len(response.context['page_obj']), 10)
        self.assertEqual(len(self.get_list(page=2).context['page_obj']), 4)

    def test_csv_export_only_contains_own_rows(self):
        response = self.client.get(reverse('export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode('utf-8-sig')
        self.assertIn('Pizza', body)
        self.assertNotIn('Bob pizza', body)

    def test_csv_export_neutralises_formulas(self):
        self.make_expense(self.alice, description='=SUM(A1:A9)')
        body = self.client.get(reverse('export_csv')).content.decode('utf-8-sig')
        self.assertIn("'=SUM(A1:A9)", body)


# --------------------------------------------------------------------------
# Dashboard & budget
# --------------------------------------------------------------------------

class DashboardTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def test_dashboard_totals_and_chart_data(self):
        today = timezone.localdate()
        self.make_expense(self.alice, category='Food', amount=Decimal('100'), date=today)
        self.make_expense(self.alice, category='Travel', amount=Decimal('50'), date=today)
        self.make_expense(self.alice, category='Food', amount=Decimal('25'), date=today.replace(day=1) - timedelta(days=1))
        self.make_expense(self.bob, category='Food', amount=Decimal('999'), date=today)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['month_total'], Decimal('150'))
        self.assertEqual(response.context['all_total'], Decimal('175'))
        self.assertEqual(response.context['entry_count'], 3)
        chart = response.context['chart_data']
        self.assertEqual(chart['category']['labels'], ['Food', 'Travel'])
        self.assertEqual(len(chart['trend']['labels']), 6)
        self.assertEqual(chart['trend']['values'][-1], 150.0)
        self.assertEqual(chart['trend']['values'][-2], 25.0)

    def test_dashboard_with_no_data(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['all_total'], Decimal('0'))
        self.assertIsNone(response.context['budget'])


class BudgetTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def test_set_and_update_budget(self):
        self.client.post(reverse('budget'), {'monthly_limit': '5000'})
        self.assertEqual(Budget.objects.get(owner=self.alice).monthly_limit, Decimal('5000.00'))
        self.client.post(reverse('budget'), {'monthly_limit': '7000'})
        self.assertEqual(Budget.objects.filter(owner=self.alice).count(), 1)
        self.assertEqual(Budget.objects.get(owner=self.alice).monthly_limit, Decimal('7000.00'))

    def test_budget_must_be_positive(self):
        response = self.client.post(reverse('budget'), {'monthly_limit': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Budget.objects.exists())

    def test_budget_progress_and_over_budget(self):
        Budget.objects.create(owner=self.alice, monthly_limit=Decimal('100'))
        self.make_expense(self.alice, amount=Decimal('150'))
        info = self.client.get(reverse('dashboard')).context['budget']
        self.assertTrue(info['over'])
        self.assertEqual(info['percent'], 100)
        self.assertEqual(info['level'], 'danger')
        self.assertEqual(info['over_by'], Decimal('50'))

    def test_budgets_are_private(self):
        Budget.objects.create(owner=self.bob, monthly_limit=Decimal('100'))
        self.assertIsNone(self.client.get(reverse('dashboard')).context['budget'])

    def test_remove_budget(self):
        Budget.objects.create(owner=self.alice, monthly_limit=Decimal('100'))
        self.assertEqual(self.client.get(reverse('remove_budget')).status_code, 405)
        self.client.post(reverse('remove_budget'))
        self.assertFalse(Budget.objects.exists())


class MiscTests(TestCase):
    def test_health_check_needs_no_login(self):
        response = self.client.get(reverse('healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')


# --------------------------------------------------------------------------
# Payment mode (offline / online + app)
# --------------------------------------------------------------------------

class PaymentModeTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def add(self, **overrides):
        return self.client.post(reverse('add_expense'), self.post_data(**overrides))

    def test_add_online_expense_with_app(self):
        response = self.add(payment_mode='online', payment_app='gpay')
        self.assertRedirects(response, reverse('expense_list'))
        expense = Expense.objects.get()
        self.assertEqual((expense.payment_mode, expense.payment_app), ('online', 'gpay'))
        self.assertEqual(expense.payment_label, 'Google Pay')

    def test_online_expense_needs_an_app(self):
        response = self.add(payment_mode='online', payment_app='')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_offline_expense_is_cash_and_ignores_app(self):
        self.add(payment_mode='offline', payment_app='gpay')
        expense = Expense.objects.get()
        self.assertEqual((expense.payment_mode, expense.payment_app), ('offline', ''))
        self.assertEqual(expense.payment_label, 'Cash')

    def test_payment_mode_is_required(self):
        data = self.post_data()
        del data['payment_mode']
        response = self.client.post(reverse('add_expense'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_rejects_unknown_app(self):
        response = self.add(payment_mode='online', payment_app='not-an-app')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_edit_can_switch_cash_to_online(self):
        expense = self.make_expense(self.alice, payment_mode='offline')
        self.client.post(
            reverse('edit_expense', args=[expense.id]),
            self.post_data(payment_mode='online', payment_app='phonepe'),
        )
        expense.refresh_from_db()
        self.assertEqual((expense.payment_mode, expense.payment_app), ('online', 'phonepe'))

    def test_old_expenses_without_a_mode_still_work(self):
        self.make_expense(self.alice)  # payment_mode left blank, like rows from before this feature
        self.assertEqual(self.client.get(reverse('expense_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertEqual(Expense.objects.get().payment_label, '')

    def test_filter_by_mode_and_app(self):
        self.make_expense(self.alice, description='cash one', payment_mode='offline')
        self.make_expense(self.alice, description='gpay one', payment_mode='online', payment_app='gpay')
        self.make_expense(self.alice, description='card one', payment_mode='online', payment_app='card')
        url = reverse('expense_list')
        self.assertEqual(self.client.get(url, {'mode': 'online'}).context['result_count'], 2)
        self.assertEqual(self.client.get(url, {'mode': 'offline'}).context['result_count'], 1)
        self.assertEqual(self.client.get(url, {'app': 'gpay'}).context['result_count'], 1)

    def test_dashboard_payment_breakdown(self):
        self.make_expense(self.alice, amount=Decimal('300'), payment_mode='online', payment_app='gpay')
        self.make_expense(self.alice, amount=Decimal('100'), payment_mode='offline')
        self.make_expense(self.bob, amount=Decimal('999'), payment_mode='online', payment_app='gpay')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['online_total'], Decimal('300'))
        self.assertEqual(response.context['offline_total'], Decimal('100'))
        self.assertEqual(response.context['online_percent'], 75)
        self.assertEqual(response.context['offline_percent'], 25)
        labels = [row['label'] for row in response.context['payment_rows']]
        self.assertEqual(labels, ['Google Pay', 'Cash'])

    def test_csv_has_payment_columns(self):
        self.make_expense(self.alice, payment_mode='online', payment_app='navi')
        body = self.client.get(reverse('export_csv')).content.decode('utf-8-sig')
        self.assertIn('Payment mode', body)
        self.assertIn('Online', body)
        self.assertIn('Navi', body)


class PaymentSplitTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)
        self.make_expense(self.alice, category='Food', amount=Decimal('300'), payment_mode='online', payment_app='gpay')
        self.make_expense(self.alice, category='Food', amount=Decimal('100'), payment_mode='offline')
        self.make_expense(self.alice, category='Travel', amount=Decimal('50'))  # old row, no mode
        self.make_expense(self.bob, category='Food', amount=Decimal('999'), payment_mode='online', payment_app='gpay')

    def get_list(self, **params):
        return self.client.get(reverse('expense_list'), params)

    def test_split_without_filters(self):
        response = self.get_list()
        self.assertEqual(response.context['result_total'], Decimal('450'))
        self.assertEqual(response.context['split'], {
            'online': Decimal('300'), 'offline': Decimal('100'), 'unset': Decimal('50'),
        })
        self.assertFalse(response.context['payment_filtered'])

    def test_split_still_shows_both_when_a_mode_is_chosen(self):
        response = self.get_list(mode='online')
        self.assertEqual(response.context['result_total'], Decimal('300'))
        self.assertEqual(response.context['split']['online'], Decimal('300'))
        self.assertEqual(response.context['split']['offline'], Decimal('100'))
        self.assertTrue(response.context['payment_filtered'])

    def test_split_follows_the_other_filters(self):
        response = self.get_list(category='Travel')
        self.assertEqual(response.context['split']['online'], Decimal('0'))
        self.assertEqual(response.context['split']['unset'], Decimal('50'))

    def test_split_never_includes_other_users(self):
        response = self.get_list()
        self.assertNotEqual(response.context['split']['online'], Decimal('1299'))

    def test_page_shows_online_and_cash_amounts(self):
        response = self.get_list()
        self.assertContains(response, '₹300.00')  # online
        self.assertContains(response, '₹100.00')  # cash
