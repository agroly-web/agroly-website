from django.db import migrations, models


def isi_numbering_customer(apps, schema_editor):
    Customer = apps.get_model("relasi_bisnis", "Customer")
    urutan = 0
    for customer in Customer.objects.order_by("id"):
        urutan += 1
        customer.numbering = f"C-{urutan:02d}"
        customer.save(update_fields=["numbering"])


def kosongkan_numbering(apps, schema_editor):
    Customer = apps.get_model("relasi_bisnis", "Customer")
    Customer.objects.update(numbering=None)


class Migration(migrations.Migration):

    dependencies = [
        ("relasi_bisnis", "0003_supplier_numbering"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="numbering",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(isi_numbering_customer, kosongkan_numbering),
        migrations.AlterField(
            model_name="customer",
            name="numbering",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]
