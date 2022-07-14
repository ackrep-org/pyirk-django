import pyerk
from .models import Entity, LanguageSpecifiedString as LSS


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

    # TODO: remove dublications

    # recreate the databse content:items
    for itm in pyerk.ds.items.values():
        label = LSS.objects.create(langtag="en", content=getattr(itm, "R1", None))
        e = Entity.objects.create(
            key_str=itm.short_key,
            description=getattr(itm, "R2", None),
        )
        e.label.add(label)

    # same for relations
    for rel in pyerk.ds.relations.values():
        label = LSS.objects.create(langtag="en", content=getattr(rel, "R1", None))
        e = Entity.objects.create(
            key_str=rel.short_key,
            description=getattr(rel, "R2", None),
        )
        e.label.add(label)
