from django.db import models
from django.conf import settings


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

    def get_label(self, langtag=None) -> str:
        if langtag is None:
            langtag = settings.DEFAULT_DATA_LANGUAGE
        res = self.label.filter(langtag=langtag)
        if len(res) == 0:
            return f"[no label in language {langtag} available]"
        else:
            return res[0].content

    def __str__(self) -> str:
        return self.get_label()


