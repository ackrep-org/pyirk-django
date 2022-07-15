import itertools
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

    # repopulate the databse with items and relations (and auxiliary objects)
    for ent in itertools.chain(pyerk.ds.items.values(), pyerk.ds.relations.values()):
        label = create_lss(ent, "R1")
        e = Entity.objects.create(
            key_str=ent.short_key,
            description=getattr(ent, "R2", None),
        )
        e.label.add(label)


def create_lss(ent: pyerk.Entity, rel_key: str) -> LSS:
    rdf_literal = pyerk.aux.ensure_rdf_str_literal(getattr(ent, rel_key, ""))
    return LSS.objects.create(langtag=rdf_literal.language, content=rdf_literal.value)
