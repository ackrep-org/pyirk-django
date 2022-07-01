from django.db import models

# Create your models here.


class Item(models.Model):
    id = models.BigAutoField(primary_key=True)
    key_str = models.TextField(default="(unknown key)")
    label = models.TextField(default="", null=True)
    description = models.TextField(default="", null=True)

    objects = models.Manager()  # make PyCharm happy

    def __str__(self):
        return self.label
