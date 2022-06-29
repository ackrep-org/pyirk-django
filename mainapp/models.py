from django.db import models

# Create your models here.


class Item(models.Model):
    label = models.TextField()

    def __str__(self):
        return self.label
