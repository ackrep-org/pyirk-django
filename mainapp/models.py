from django.db import models

# Create your models here.


class Item(models.Model):
    id = models.BigAutoField(primary_key=True)
    label = models.TextField()

    objects = models.Manager()  # make PyCharm happy

    def __str__(self):
        return self.label
