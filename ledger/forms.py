from django import forms

from expenses.models import Expense

from .models import Income, Loan, Repayment

# Suggestions for the "Source" box on the Income form. Users can type anything.
INCOME_SOURCES = ['Salary', 'Freelance', 'Business', 'Gift', 'Interest', 'Refund', 'Other']


class _BootstrapMixin:
    """Adds the 'form-control' / 'form-select' class to every field."""

    def _style_fields(self):
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css


def _date_input():
    return forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'})


def _amount_input():
    return forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})


class PaymentForm(forms.ModelForm):
    """Base form: adds the cash/online choice and the app used (same as for expenses)."""

    payment_mode = forms.ChoiceField(
        choices=Expense.PAYMENT_MODE_CHOICES,
        widget=forms.RadioSelect,
        label='Payment mode',
        error_messages={'required': 'Choose how the money moved: offline or online.'},
    )
    payment_app = forms.ChoiceField(
        choices=[('', 'Select app / method')] + Expense.PAYMENT_APP_CHOICES,
        required=False,
        label='Paid using',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('payment_mode')
        if mode == Expense.ONLINE and not cleaned.get('payment_app'):
            self.add_error('payment_app', 'Select which app or method was used.')
        elif mode == Expense.OFFLINE:
            cleaned['payment_app'] = ''
        return cleaned


# --------------------------------------------------------------------------
# Income
# --------------------------------------------------------------------------

class IncomeForm(PaymentForm):
    class Meta:
        model = Income
        fields = ['date', 'source', 'description', 'amount', 'payment_mode', 'payment_app']
        widgets = {
            'date': _date_input(),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'list': 'source-options',
                'placeholder': 'Salary, Freelance, Gift...',
                'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': _amount_input(),
        }
        labels = {'source': 'Received from'}

    def clean_source(self):
        return self.cleaned_data['source'].strip().title()


class IncomeFilterForm(_BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label='Search')
    start = forms.DateField(required=False, label='From', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    end = forms.DateField(required=False, label='To', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['q'].widget.attrs['placeholder'] = 'Search source or note'
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start'), cleaned.get('end')
        if start and end and start > end:
            raise forms.ValidationError('"From" date must not be after "To" date.')
        return cleaned


# --------------------------------------------------------------------------
# Loans
# --------------------------------------------------------------------------

class LoanForm(PaymentForm):
    direction = forms.ChoiceField(
        choices=Loan.DIRECTION_CHOICES,
        widget=forms.RadioSelect,
        label='Type',
        error_messages={'required': 'Choose whether you lent or borrowed the money.'},
    )

    class Meta:
        model = Loan
        fields = ['direction', 'person', 'date', 'amount', 'due_date', 'note', 'payment_mode', 'payment_app']
        widgets = {
            'person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of the person'}),
            'date': _date_input(),
            'amount': _amount_input(),
            'due_date': _date_input(),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {'person': 'Person', 'date': 'Date given / taken', 'due_date': 'Return by'}

    def clean_person(self):
        return self.cleaned_data['person'].strip().title()

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.instance.pk:  # editing: cannot drop below what has already come back
            repaid = self.instance.repaid_amount
            if amount < repaid:
                raise forms.ValidationError(f'Amount cannot be less than the ₹{repaid:.2f} already repaid.')
        return amount

    def clean(self):
        cleaned = super().clean()
        date, due = cleaned.get('date'), cleaned.get('due_date')
        if date and due and due < date:
            self.add_error('due_date', '"Return by" cannot be before the date the money was given / taken.')
        return cleaned


class LoanFilterForm(_BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label='Person')
    direction = forms.ChoiceField(
        required=False, label='Type',
        choices=[('', 'Lent and borrowed')] + Loan.DIRECTION_CHOICES,
    )
    status = forms.ChoiceField(
        required=False, label='Status',
        choices=[('', 'All'), ('open', 'Not fully repaid'), ('settled', 'Settled')],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['q'].widget.attrs['placeholder'] = 'Search by name'
        self._style_fields()


# --------------------------------------------------------------------------
# Repayments
# --------------------------------------------------------------------------

class RepaymentForm(PaymentForm):
    class Meta:
        model = Repayment
        fields = ['date', 'amount', 'note', 'payment_mode', 'payment_app']
        widgets = {
            'date': _date_input(),
            'amount': _amount_input(),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }

    def __init__(self, *args, loan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.loan = loan

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.loan is not None and amount > self.loan.remaining:
            raise forms.ValidationError(f'Only ₹{self.loan.remaining:.2f} is still pending on this loan.')
        return amount
