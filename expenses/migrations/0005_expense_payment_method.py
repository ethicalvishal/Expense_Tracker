from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0004_budget_and_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='payment_mode',
            field=models.CharField(
                blank=True,
                choices=[('offline', 'Offline (Cash)'), ('online', 'Online')],
                default='',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='expense',
            name='payment_app',
            field=models.CharField(
                blank=True,
                choices=[
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
                ],
                default='',
                max_length=12,
            ),
        ),
    ]
