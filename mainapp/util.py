import itertools
import urllib
from django.db.utils import OperationalError
from django.conf import settings
from django.db import transaction
from django.urls import reverse

import pyerk
# noinspection PyUnresolvedReferences
from pyerk import (
    u,  # convenience function to convert a key into an URI
    auxiliary as aux,
)
from .models import Entity, LanguageSpecifiedString as LSS


def reload_data(omit_reload=False, speedup: bool = True) -> None:
    """
    Load data from python-module into data base to allow simple searching

    :param omit_reload: default False; flag to control whether the module should be reloaded if it was already loaded
    :param speedup:     default True; flag to determine if transaction.set_autocommit(False) should be used
                        this significantly speeds up the start of the development server but does not work well
                        with django.test.TestCase (where we switch it off)
    :return:
    """

    mod = pyerk.erkloader.load_mod_from_path(
        settings.ERK_DATA_PATH, prefix="ct", modname=settings.ERK_DATA_MOD_NAME, omit_reload=omit_reload
    )

    if mod is None:
        # this was an omited reload
        return

    # delete all existing data (if database already exisits)
    try:
        Entity.objects.all().delete()
    except OperationalError:
        # db does not yet exist. The functions is probably called during `manage.py migrate` or similiar.
        return

    if settings.RUNNING_TESTS:
        speedup = False

    # repopulate the databse with items and relations (and auxiliary objects)
    _load_entities_to_db(speedup=speedup)


def _load_entities_to_db(speedup: bool) -> None:

    # this pattern is based on https://stackoverflow.com/a/31822405/333403
    try:
        if speedup:
            transaction.set_autocommit(False)
        __load_entities_to_db(speedup=speedup)
    except Exception:
        if speedup:
            transaction.rollback()
        raise
    else:
        if speedup:
            transaction.commit()
    finally:
        if speedup:
            from ipydex import IPS, activate_ips_on_exception

            transaction.set_autocommit(True)


def __load_entities_to_db(speedup: bool) -> None:
    """

    :param speedup:     default True; determine if db-commits are switched to "manual mode" to leverate bullk operations
    :return:
    """

    import time

    t0 = time.time()
    entity_list = []
    label_list = []
    for ent in itertools.chain(pyerk.ds.items.values(), pyerk.ds.relations.values()):
        label = create_lss(ent, "R1")
        entity = Entity(uri=ent.uri, description=getattr(ent, "R2", None))

        label_list.append(label)
        entity_list.append(entity)

    # print(pyerk.auxiliary.bcyan(f"time1: {time.time() - t0}"))
    Entity.objects.bulk_create(entity_list)
    LSS.objects.bulk_create(label_list)

    if speedup:
        transaction.commit()

    for entity, label in zip(Entity.objects.all(), LSS.objects.all()):
        entity.label.add(label)

    # print(pyerk.auxiliary.bcyan(f"time2: {time.time() - t0}"))


def create_lss(ent: pyerk.Entity, rel_key: str) -> LSS:
    """
    Create a language specified string (see models.LanguageSpecifiedString).
    Note: the object is not yet commited to the database.

    :param ent:
    :param rel_key:
    :return:
    """
    rdf_literal = pyerk.aux.ensure_rdf_str_literal(getattr(ent, rel_key, ""))
    return LSS(langtag=rdf_literal.language, content=rdf_literal.value)


def urlquote(txt):
    # noinspection PyUnresolvedReferences
    return urllib.parse.quote(txt, safe="")


def w(key_str: str) -> str:
    """
    Call pyerk.u(*args) (convert (builtin) key to uri) and pass it through urlib.parse.quote

    :param key_str:     see pyerk.u
    :return:
    """

    res = pyerk.u(key_str)
    return urlquote(res)


def q_reverse(pagename, uri, **kwargs):
    """
    Simplifies the hazzle for passing URIs into `reverse` (they must be percent-encoded therefor, aka quoted), and then
    unqoting the result again.


    :param pagename:
    :param uri:
    :param kwargs:
    :return:
    """

    quoted_url = reverse(pagename, kwargs={"uri": urlquote(uri)})

    # noinspection PyUnresolvedReferences
    return quoted_url
