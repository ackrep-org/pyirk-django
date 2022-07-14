from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True
    objects = models.Manager()  # make PyCharm happy


class LanguageSpecifiedString(BaseModel):
    id = models.BigAutoField(primary_key=True)
    langtag = models.CharField(max_length=8, default="", null=False)
    content = models.TextField(null=True)

    def __repr__(self):
        return f"<LSS({self.content}@{self.langtag})>"


class Entity(BaseModel):
    id = models.BigAutoField(primary_key=True)

    # TODO: this should be renamed to `short_key`
    key_str = models.TextField(default="(unknown key)")
    label = models.ManyToManyField(LanguageSpecifiedString)
    description = models.TextField(default="", null=True)

    def __str__(self):
        return self.label


