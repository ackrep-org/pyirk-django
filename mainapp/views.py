from typing import Union
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.urls import reverse
from django.db.models import Q
import pyerk
from . import util

from ipydex import IPS

from .models import Entity


def home_page_view(request):

    # TODO: in the future this should not be triggered on every page refresh
    util.reload_data(omit_reload=True)

    context = dict(greeting_message="Hello, World!")

    return render(request, 'mainapp/page-landing.html', context)


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")

    payload = []
    if q:
        entities = Entity.objects.filter(Q(label__icontains=q) | Q(key_str__icontains=q))

        for idx, db_entity in enumerate(entities):
            db_entity: Entity

            payload.append(render_entity_list_entry(db_entity, idx, script_tag="script"))

    return JsonResponse({"status": 200, "data": payload})


def render_entity_list_entry(db_entity: Entity, idx, script_tag="myscript") -> str:

    if isinstance(db_entity, str):
        db_entity = get_object_or_404(Entity, key_str=db_entity)

    template = get_template("mainapp/widget-entity-list-entry.html")
    ctx = {
        "key_str": db_entity.key_str,
        "label": db_entity.label,
        "description": db_entity.description,
        "url": reverse("entitypage", kwargs={"key_str": db_entity.key_str}),
        "idx": idx,
        "script_tag": script_tag,
    }
    rendered_entity = template.render(context=ctx)
    return rendered_entity


def mockup(request):
    db_entity = get_object_or_404(Entity, key_str="I5")
    rendered_entity = render_entity_list_entry(db_entity, idx=23, script_tag="script")
    context = dict(greeting_message="Hello, World!", rendered_entity=rendered_entity)

    return render(request, 'mainapp/page-searchresult-test.html', context)


def entity_view(request, key_str=None):
    # TODO: in the future this should not be triggered on every page refresh
    util.reload_data(omit_reload=True)

    db_entity = get_object_or_404(Entity, key_str=key_str)
    rendered_entity = render_entity_inline(db_entity)
    rendered_entity_relations = render_entity_relations(db_entity)
    # rendered_entity_context_vars = render_entity_context_vars(db_entity)
    rendered_entity_scopes = render_entity_scopes(db_entity)

    context = dict(
        rendered_entity=rendered_entity,
        entity=db_entity,
        rendered_entity_relations=rendered_entity_relations,
        # rendered_entity_context_vars=rendered_entity_context_vars,
        rendered_entity_scopes=rendered_entity_scopes,
    )
    return render(request, 'mainapp/page-entity-detail.html', context)


def render_entity_inline(db_entity: Entity) -> str:

    entity_dict = represent_entity_as_dict(pyerk.ds.get_entity(db_entity.key_str))
    template = get_template(entity_dict["template"])

    ctx = {
        "c": entity_dict
    }
    rendered_entity = template.render(context=ctx)
    return rendered_entity


def render_entity_relations(db_entity: Entity) -> str:

    # omit information which is already displayed by render_entity (label, description)
    black_listed_keys = ["R1", "R2"]
    short_key = db_entity.key_str

    # #########################################################################
    # frist: handle direct relations (where `db_entity` is subject)
    # #########################################################################

    # dict like {"R1": [<RelationEdge 1234>, ...], "R2": [...]}
    relation_edges0 = pyerk.ds.relation_edges[short_key]

    # create a flat list of template-friendly dicts
    re_dict_2tuples = []
    for rel_key, re_list in relation_edges0.items():
        if rel_key in black_listed_keys:
            continue
        for re in re_list:
            # index 0 is the subject entity which is db_entity and thus not relevant here
            d1 = represent_entity_as_dict(re.relation_tuple[1])
            d2 = represent_entity_as_dict(re.relation_tuple[2])
            re_dict_2tuples.append((d1, d2))

    # #########################################################################
    # second: handle inverse relations (where `db_entity` is object)
    # #########################################################################

    # dict like {"R4": [<RelationEdge 1234>, ...], "R8": [...]}
    inv_relation_edges0 = pyerk.ds.inv_relation_edges[short_key]

    # create a flat list of template-friendly dicts
    inv_re_dict_2tuples = []
    for rel_key, inv_re_list in inv_relation_edges0.items():
        if rel_key in black_listed_keys:
            continue
        for re in inv_re_list:
            # index 2 is the object entity of the inverse relations which is db_entity and thus not relevant here
            d0 = represent_entity_as_dict(re.relation_tuple[0])
            d1 = represent_entity_as_dict(re.relation_tuple[1])
            inv_re_dict_2tuples.append((d0, d1))

    # #########################################################################
    # third: render the two lists and return
    # #########################################################################

    ctx = {
        "main_entity": represent_entity_as_dict(pyerk.ds.get_entity(short_key)),
        "re_dict_2tuples": re_dict_2tuples,
        "inv_re_dict_2tuples": inv_re_dict_2tuples,
    }
    template = get_template("mainapp/widget-entity-relations.html")
    render_result = template.render(context=ctx)

    return render_result


def render_entity_scopes(db_entity: Entity) -> str:
    code_entity = pyerk.ds.get_entity(db_entity.key_str)
    # noinspection PyProtectedMember
    for ns_name, ns in code_entity._namespaces.items():
        pass

    scopes = pyerk.get_scopes(code_entity)

    scope_contents = []
    for scope in scopes:

        items = pyerk.get_items_defined_in_scope(scope)
        re: pyerk.RelationEdge
        # currently we only use `R4__instance_of` as "defining relation"
        # relation_edges = [re for key, re_list in relation_edges0.items() if key not in black_listed_keys for re in re_list]
        defining_relation_triples = []
        for item in items:
            for re in pyerk.ds.relation_edges[item.short_key]["R4"]:
                defining_relation_triples.append(list(map(represent_entity_as_dict, re.relation_tuple)))

        scope_contents.append({
            "name": scope.R1,
            "defining_relations": defining_relation_triples,
        })

    ctx = {
        "scopes": scope_contents
    }

    template = get_template("mainapp/widget-entity-scopes.html")
    render_result = template.render(context=ctx)
    # IPS()
    return render_result


# noinspection PyUnresolvedReferences
def represent_entity_as_dict(code_entity: Union[Entity, object]) -> dict:

    if isinstance(code_entity, pyerk.Entity):
        res = {
            "short_key": code_entity.short_key,
            "label": code_entity.R1,
            "description": code_entity.R2,
            "detail_url": reverse("entitypage", kwargs={"key_str": code_entity.short_key}),
            "template": "mainapp/widget-entity-inline.html",
        }
    else:
        # assume we have a literal
        res = {
            "value": repr(code_entity),
            "template": "mainapp/widget-literal-inline.html",
        }

    return res


# TODO: obsolete?
"""
def render_entity_context_vars(db_entity: Entity) -> str:
    template = get_template("mainapp/widget-entity-context-vars.html")
    code_entity = pyerk.ds.get_entity(db_entity.key_str)
    context_vars0 = getattr(code_entity, "_context_vars", dict()).items()

    context_vars = []
    for i, (name, var) in enumerate(context_vars0):
        if isinstance(var, pyerk.GenericInstance):
            context_vars.append((name, "GenericInstance of", render_entity(var.cls.short_key, i, script_tag=None)))
        else:
            context_vars.append((name, "is", render_entity(var.cls.short_key, i)))

    ctx = {
        "context_vars": context_vars
    }
    render_result = template.render(context=ctx)
    return render_result
"""


def debug_view(request, xyz=0):

    z = 1

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    return HttpResponse(f'Some plain message {xyz}')
