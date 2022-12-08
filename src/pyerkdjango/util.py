import time
import os
import itertools
import urllib
import shutil
from django.db.utils import OperationalError
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from addict import Addict as Container

import pyerk
# noinspection PyUnresolvedReferences
from pyerk import (  # noqa
    u,  # convenience function to convert a key into an URI
    auxiliary as aux,
)
from .models import Entity, LanguageSpecifiedString as LSS


def reload_data_if_necessary(force: bool = False, speedup: bool = True) -> Container:
    res = Container()
    res.modules = reload_modules_if_necessary(force=force)

    # TODO: test if db needs to be reloaded
    res.db = load_erk_entities_to_db(speedup=speedup)

    return res


# TODO: a config file should specify which modules to load
def reload_modules_if_necessary(force: bool = False) -> int:
    count = 0

    # TODO: this should be read from a config file

    # load ocse
    if force or pyerk.settings.OCSE_URI not in pyerk.ds.uri_prefix_mapping.a:
        LC = settings.LC
        _ = pyerk.erkloader.load_mod_from_path(
            LC.ERK_DATA_MAIN_MOD, prefix=LC.ERK_DATA_MAIN_MOD_PREFIX, modname=LC.ERK_DATA_MAIN_MOD_NAME,
        )
        count += 1

    # TODO: remove this obsolete code
    if 0:
        # load ackrep entities
        if force or pyerk.ackrep_parser.__URI__ not in pyerk.ds.uri_prefix_mapping.a:
            pyerk.ackrep_parser.load_ackrep_entities(base_path=None, strict=True)
            count += 1

    return count


def load_erk_entities_to_db(speedup: bool = True) -> int:
    """
    Load data from python-module into data base to allow simple searching

    :param speedup:     default True; flag to determine if transaction.set_autocommit(False) should be used
                        this significantly speeds up the start of the development server but does not work well
                        with django.test.TestCase (where we switch it off)

    :return:            number of entities loaded
    """

    # delete all existing data (if database already exisits)
    try:
        Entity.objects.all().delete()
        LSS.objects.all().delete()
    except OperationalError:
        # db does not yet exist. The functions is probably called during `manage.py migrate` or similiar.
        return 0

    if settings.RUNNING_TESTS:
        speedup = False

    # repopulate the databse with items and relations (and auxiliary objects)
    _load_entities_to_db(speedup=speedup)

    n = len(Entity.objects.all())
    n += len(LSS.objects.all())

    return n


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
            transaction.set_autocommit(True)


def __load_entities_to_db(speedup: bool) -> None:
    """

    :param speedup:   default True; determine if db-commits are switched to "manual mode" to leverage bulk operations
    :return:
    """

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

    assert len(Entity.objects.all()) == len(LSS.objects.all()), "Mismatch in Entities and corresponding Labels."
    for entity, label in zip(Entity.objects.all(), LSS.objects.all()):
        entity.label.add(label)

    # print(pyerk.auxiliary.bcyan(f"time2: {time.time() - t0}"))


def unload_data(strict=False):

    # unload all loaded modules
    for uri, name in pyerk.ds.modnames.items():
        pyerk.unload_mod(uri, strict=strict)

    # unload db
    Entity.objects.all().delete()
    LSS.objects.all().delete()


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


def mkdir_p(path):
    """
    create a path and accept if it already exists
    """
    try:
        os.makedirs(path)
    except OSError:
        pass


def savetxt(fpath: str, file_content: str, backup=True) -> None:

    if not os.path.exists(fpath):
        backup = False

    parent_path, fname = os.path.split(fpath)

    if backup:

        backup_dir = os.path.join(parent_path, "_backup")

        tstamp = time.strftime("%Y-%m-%d__%H-%M-%S")
        root_name, ext = os.path.splitext(fname)
        backup_path = os.path.join(backup_dir, f"{root_name}_{tstamp}{ext}")

        mkdir_p(backup_dir)
        shutil.copy(fpath, backup_path)

    with open(fpath, "w") as fp:
        fp.write(file_content)


# TODO: obsolete?
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
