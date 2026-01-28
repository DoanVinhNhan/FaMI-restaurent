# Generated migration for adding promotion snapshot fields to Invoice and Transaction
from django.db import migrations, models
import decimal
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0008_alter_order_status_alter_orderdetail_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='promotion',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='sales.Promotion'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='invoice',
            name='original_total',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='transaction',
            name='promotion',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='sales.Promotion'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12),
        ),
    ]
