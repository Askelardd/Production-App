from django.db import migrations

def copy_plants(apps, schema_editor):
    Order = apps.get_model('theme', 'Order')
    Plant = apps.get_model('theme', 'Plant')

    for order in Order.objects.all():
        if order.plant: # Se houver texto no campo antigo
            # Cria a Plant se não existir, ou vai buscá-la se já existir
            plant_obj, created = Plant.objects.get_or_create(name=order.plant)
            # Associa a ForeignKey ao novo campo
            order.plant_fk = plant_obj
            order.save()

class Migration(migrations.Migration):

    dependencies = [
        ('theme', '0121_plant_order_plant_fk'),
    ]

    operations = [
        migrations.RunPython(copy_plants),
    ]