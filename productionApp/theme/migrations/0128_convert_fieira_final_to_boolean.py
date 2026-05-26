# Generated migration to convert fieira_final from bytea to boolean

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('theme', '0127_alter_dieinstance_fieira_final'),
    ]

    operations = [
        # Remove the current field
        migrations.RemoveField(
            model_name='dieinstance',
            name='fieira_final',
        ),
        # Recreate it as BooleanField
        migrations.AddField(
            model_name='dieinstance',
            name='fieira_final',
            field=models.BooleanField(default=False),
        ),
    ]
