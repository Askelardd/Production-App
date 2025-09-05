from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('theme', '0055_order_arriving_date_order_plant_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE theme_orderscoming
                ADD COLUMN IF NOT EXISTS data_done date NULL;
            """,
            reverse_sql="""
                ALTER TABLE theme_orderscoming
                DROP COLUMN IF EXISTS data_done;
            """
        ),
    ]
