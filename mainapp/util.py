import pyerk
from .models import Entity


def reload_data(omit_reload=False) -> None:
    """
    Load data from python-module into data base to allow simple searching
    :return:
    """

    mod = pyerk.erkloader.load_mod_from_path(
        "../controltheory_experiments/knowledge_base1.py", "knowledge_base1", omit_reload=omit_reload
    )

    if mod is None:
        # this was an omited reload
        return

    # delete all existing data
    Entity.objects.all().delete()

    for itm in pyerk.ds.items.values():
        Entity.objects.create(
            key_str=itm.short_key,
            label=getattr(itm, "R1", None),
            description=getattr(itm, "R2", None),
        )

    for rel in pyerk.ds.relations.values():
        Entity.objects.create(
            key_str=rel.short_key,
            label=getattr(rel, "R1", None),
            description=getattr(rel, "R2", None),
        )
