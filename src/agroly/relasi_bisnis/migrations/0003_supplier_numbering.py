from django.db import migrations, models


def isi_numbering_supplier(apps, schema_editor):
    Supplier = apps.get_model("relasi_bisnis", "Supplier")
    urutan = 0
    for supplier in Supplier.objects.order_by("id"):
        urutan += 1
        supplier.numbering = f"S-{urutan:02d}"
        supplier.save(update_fields=["numbering"])


def kosongkan_numbering(apps, schema_editor):
    Supplier = apps.get_model("relasi_bisnis", "Supplier")
    Supplier.objects.update(numbering=None)


class Migration(migrations.Migration):

    dependencies = [
        ("relasi_bisnis", "0002_customer_no_kartu_customer_saldo_saat_ini_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="numbering",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(isi_numbering_supplier, kosongkan_numbering),
        migrations.AlterField(
            model_name="supplier",
            name="numbering",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]
