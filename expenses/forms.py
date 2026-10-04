from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Budget, Expense

User = get_user_model()

# Suggestions shown in the category box. Users can still type anything.
CATEGORY_SUGGESTIONS = [
    'Food', 'Travel', 'Shopping', 'Bills', 'Health',
    'Entertainment', 'Education', 'Other',
]


class _BootstrapMixin:
    """Adds Bootstrap classes to every field of a form."""

    def _style_fields(self):
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css


# --------------------------------------------------------------------------
# Expenses
# --------------------------------------------------------------------------

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        # "owner" is deliberately not here: the view sets it from request.user,
        # so nobody can create an expense for someone else.
        fields = ['date', 'category', 'description', 'amount']
        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'list': 'category-options',
                'placeholder': 'Food, Travel, Shopping...',
                'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
        }

    def clean_category(self):
        # "food", "FOOD" and "Food" should all count as the same category.
        return self.cleaned_data['category'].strip().title()


class ExpenseFilterForm(_BootstrapMixin, forms.Form):
    """Search / filter box on the expenses page (all fields optional)."""

    q = forms.CharField(required=False, label='Search')
    category = forms.ChoiceField(required=False)
    start = forms.DateField(
        required=False, label='From',
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    end = forms.DateField(
        required=False, label='To',
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        categories = (
            Expense.objects.filter(owner=user)
            .order_by('category')
            .values_list('category', flat=True)
            .distinct()
        )
        self.fields['category'].choices = [('', 'All categories')] + [(c, c) for c in categories]
        self.fields['q'].widget.attrs['placeholder'] = 'Search category or description'
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start'), cleaned.get('end')
        if start and end and start > end:
            raise forms.ValidationError('"From" date must not be after "To" date.')
        return cleaned


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['monthly_limit']
        labels = {'monthly_limit': 'Monthly budget (₹)'}
        widgets = {
            'monthly_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
        }


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

def _email_in_use(email, exclude_pk=None):
    qs = User.objects.filter(email__iexact=email)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


class SignUpForm(_BootstrapMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text='Used only to reset your password if you forget it.',
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        self.fields['username'].widget.attrs['autofocus'] = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if _email_in_use(email):
            raise forms.ValidationError('An account with this email already exists.')
        return email


class AccountForm(_BootstrapMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'email')
        labels = {'first_name': 'Name'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if _email_in_use(email, exclude_pk=self.instance.pk):
            raise forms.ValidationError('An account with this email already exists.')
        return email


class LoginForm(_BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class StyledPasswordChangeForm(_BootstrapMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class StyledPasswordResetForm(_BootstrapMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class StyledSetPasswordForm(_BootstrapMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
