from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("akuntansi", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jurnalheader",
            name="nomor_bukti",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
    ]
