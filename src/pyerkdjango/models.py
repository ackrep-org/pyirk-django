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

    # TODO: this should be renamed to `short_key` (first step: see property `short_key` below)
    uri = models.TextField(default="(unknown uri)")

    # note: in reality this a one-to-many-relationship which in principle could be modeled by a ForeignKeyField
    # on the other side. However, as we might use the LanguageSpecifiedString model also on other fields (e.g.
    # description) in the future this is not an option
    label = models.ManyToManyField(LanguageSpecifiedString)
    description = models.TextField(default="", null=True)

    def get_label(self, langtag=None) -> str:
        if langtag is None:
            langtag = settings.DEFAULT_DATA_LANGUAGE
        # noinspection PyUnresolvedReferences
        res = self.label.filter(langtag=langtag)
        if len(res) == 0:
            return f"[no label in language {langtag} available]"
        else:
            return res[0].content

    def __str__(self) -> str:
        label_str = self.get_label().replace(" ", "_")
        # TODO introduce prefixes
        return f"{self.uri}__{label_str}"

    # TODO: remove obsolete short_key
    # @property
    # def short_key(self):
    #     return self.uri
