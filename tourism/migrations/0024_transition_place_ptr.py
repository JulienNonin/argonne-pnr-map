# Generated by Django 3.0.9 on 2020-10-01 16:45

from django.db import migrations, models
import django.db.models.deletion


def add_ptr(apps, schema_editor):
    PointOfInterest = apps.get_model('tourism', 'PointOfInterest')
    for poi in PointOfInterest.objects.all():
        poi.place_ptr = poi.pk
        poi.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tourism', '0023_subcategory'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='subcategory',
            options={'verbose_name': 'sous-catégorie', 'verbose_name_plural': 'sous-catégories'},
        ),
        migrations.AddField(
            model_name='pointofinterest',
            name='place_ptr',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pointofinterest',
            name='subcategory',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='tourism.SubCategory'),
        ),
        migrations.RunPython(add_ptr),
    ]
