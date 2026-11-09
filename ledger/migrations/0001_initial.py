import django.core.validators
import django.db.models.deletion
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models

MODE_CHOICES = [('offline', 'Offline (Cash)'), ('online', 'Online')]
APP_CHOICES = [
    ('gpay', 'Google Pay'),
    ('phonepe', 'PhonePe'),
    ('paytm', 'Paytm'),
    ('bhim', 'BHIM'),
    ('navi', 'Navi'),
    ('yono', 'YONO SBI'),
    ('amazonpay', 'Amazon Pay'),
    ('card', 'Debit / Credit Card'),
    ('upi', 'UPI (other app)'),
    ('bank', 'Net Banking / Bank Transfer'),
    ('other', 'Other'),
]
MIN_AMOUNT = [django.core.validators.MinValueValidator(Decimal('0.01'))]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Income',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('source', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=MIN_AMOUNT)),
                ('payment_mode', models.CharField(blank=True, choices=MODE_CHOICES, default='', max_length=10)),
                ('payment_app', models.CharField(blank=True, choices=APP_CHOICES, default='', max_length=12)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incomes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-id']},
        ),
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('person', models.CharField(max_length=100)),
                ('direction', models.CharField(choices=[('lent', 'I lent (gave money)'), ('borrowed', 'I borrowed (took money)')], max_length=10)),
                ('date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=MIN_AMOUNT)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('note', models.TextField(blank=True)),
                ('payment_mode', models.CharField(blank=True, choices=MODE_CHOICES, default='', max_length=10)),
                ('payment_app', models.CharField(blank=True, choices=APP_CHOICES, default='', max_length=12)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-id']},
        ),
        migrations.CreateModel(
            name='Repayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=MIN_AMOUNT)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('payment_mode', models.CharField(blank=True, choices=MODE_CHOICES, default='', max_length=10)),
                ('payment_app', models.CharField(blank=True, choices=APP_CHOICES, default='', max_length=12)),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repayments', to='ledger.loan')),
            ],
            options={'ordering': ['-date', '-id']},
        ),
    ]
