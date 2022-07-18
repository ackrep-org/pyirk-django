from typing import Union
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.template.loader import get_template
from django.views import View
from django.urls import reverse
from django.db.models import Q
from textwrap import dedent as twdd
from tabulate import tabulate
import pyerk
import pyerk.rdfstack
from . import util
from addict import Dict as attr_dict

from ipydex import IPS

from .models import Entity


# when this module is loaded (i.e. when the server starts) we also want to load the data (for convenience)
util.reload_data()


def home_page_view(request):

    context = dict(greeting_message="Hello, World!")

    return render(request, "mainapp/page-landing.html", context)


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")

    payload = []
    if q:
        entities = Entity.objects.filter(
            Q(label__content__icontains=q) | Q(key_str__icontains=q) | Q(description__icontains=q)
        )

        for idx, db_entity in enumerate(entities):
            db_entity: Entity
            try:
                res = render_entity_inline(
                        db_entity, idx=idx, script_tag="script", include_description=True, highlight_text=q
                )
            except KeyError:
                # there seemse to be a bug related to data reloading and automatic key generation
                # IPS()
                raise

            payload.append(res)

    return JsonResponse({"status": 200, "data": payload})


def mockup(request):
    db_entity = get_object_or_404(Entity, key_str="I5")
    rendered_entity = render_entity_inline(db_entity, idx=23, script_tag="myscript", include_description=True)
    context = dict(greeting_message="Hello, World!", rendered_entity=rendered_entity)

    return render(request, "mainapp/page-mockup.html", context)


def entity_view(request, key_str=None):

    db_entity = get_object_or_404(Entity, key_str=key_str)
    rendered_entity = render_entity_inline(db_entity, special_class="highlight", include_description=True)
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
    return render(request, "mainapp/page-entity-detail.html", context)


def render_entity_inline(entity: Union[Entity, pyerk.Entity], **kwargs) -> str:

    # allow both models.Entity (from db) and "code-defined" pyerk.Entity
    if isinstance(entity, pyerk.Entity):
        code_entity = entity
    elif isinstance(entity, Entity):
        code_entity = pyerk.ds.get_entity(entity.key_str)
    else:
        # TODO: improve handling of literal values
        assert isinstance(entity, (str, int, float, complex))
        code_entity = entity

    entity_dict = represent_entity_as_dict(code_entity)
    template = get_template(entity_dict["template"])

    highlight_text = kwargs.pop("highlight_text", None)

    if highlight_text:
        new_data = {}
        replacement_exceptions = entity_dict.get("_replacement_exceptions", [])
        for key in entity_dict.keys():
            if key.startswith("_") or key in replacement_exceptions:
                continue
            value = entity_dict[key]
            new_key = f"hl_{key}"
            new_data[new_key] = value.replace(highlight_text, f"<strong>{highlight_text}</strong>")

        entity_dict.update(new_data)

    entity_dict.update(kwargs)

    ctx = {
        "c": entity_dict,
        #  copy some items to global context (where the template expects them)
        # background: these options are in global context because the template is also used like
        # {% include main_entity.template with c=main_entity omit_label=True %}
        # where `with c.omit_label=True` is invalid template syntax
        **{k: v for k, v in kwargs.items() if k in ("omit_label", "include_description")},
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
        "main_entity": {"special_class": "highlight", **represent_entity_as_dict(pyerk.ds.get_entity(short_key))},
        "re_dict_2tuples": re_dict_2tuples,
        "inv_re_dict_2tuples": inv_re_dict_2tuples,
    }
    template = get_template("mainapp/widget-entity-relations.html")
    render_result = template.render(context=ctx)

    return render_result


def render_entity_scopes(db_entity: Entity) -> str:
    code_entity = pyerk.ds.get_entity(db_entity.key_str)
    # noinspection PyProtectedMember

    scopes = pyerk.get_scopes(code_entity)

    scope_contents = []
    for scope in scopes:

        # #### first: handle "variables" (locally relevant items) defined in this scope

        items = pyerk.get_items_defined_in_scope(scope)
        re: pyerk.RelationEdge
        # currently we only use `R4__instance_of` as "defining relation"
        # relation_edges = [re for key, re_list in relation_edges0.items() if key not in black_listed_keys for re in re_list]
        defining_relation_triples = []
        for item in items:
            for re in pyerk.ds.relation_edges[item.short_key]["R4"]:
                defining_relation_triples.append(list(map(represent_entity_as_dict, re.relation_tuple)))

        # #### second: handle further relation triples in this scope

        statement_relations = []
        re: pyerk.RelationEdge
        for re in pyerk.ds.scope_relation_edges[scope.short_key]:
            dict_tup = tuple(represent_entity_as_dict(elt) for elt in re.relation_tuple)
            statement_relations.append(dict_tup)

        scope_contents.append(
            {
                "name": scope.R1,
                "defining_relations": defining_relation_triples,
                "statement_relations": statement_relations,
            }
        )

    ctx = {"scopes": scope_contents}

    template = get_template("mainapp/widget-entity-scopes.html")
    render_result = template.render(context=ctx)
    # IPS()
    return render_result


# noinspection PyUnresolvedReferences
def represent_entity_as_dict(code_entity: Union[Entity, object]) -> dict:

    if isinstance(code_entity, pyerk.Entity):

        # this is used where the replacement for highlighting is done
        _replacement_exceptions = []
        try:
            generalized_label = code_entity.get_ui_short_representation()
            _replacement_exceptions.append("label")
        except AttributeError:
            generalized_label = code_entity.R1

        res = {
            "short_key": code_entity.short_key,
            "label": generalized_label,
            "description": str(code_entity.R2),
            "detail_url": reverse("entitypage", kwargs={"key_str": code_entity.short_key}),
            "template": "mainapp/widget-entity-inline.html",
            "_replacement_exceptions": _replacement_exceptions
        }
    else:
        # assume we have a literal
        res = {
            "value": repr(code_entity),
            "template": "mainapp/widget-literal-inline.html",
        }

    return res


def reload_data_redirect(request, targeturl=None):
    """
    This view reloads the data and then redirects to target url

    :param request:
    :param targeturl:
    :return:
    """
    if targeturl is None:
        targeturl = "/"
    util.reload_data(omit_reload=False)

    return HttpResponseRedirect(targeturl)


# this was taken from ackrep
class SearchSparqlView(View):
    def get(self, request):
        context = {}
        c = attr_dict()

        example_query = twdd(pyerk.rdfstack.get_sparql_example_query())
        qsrc = context["query"] = request.GET.get("query", example_query)

        try:
            tmp_results = pyerk.rdfstack.perform_sparql_query(qsrc)
            sparql_vars = [str(v) for v in tmp_results.vars]
            c.results = pyerk.aux.apply_func_to_table_cells(render_entity_inline, tmp_results)
        except pyerk.rdfstack.ParseException as e:
            context["err"] = f"The following error occurred: {type(e).__name__}: {str(e)}"
            c.results = []
            sparql_vars = []

        c.tab = tabulate(c.results, headers=sparql_vars, tablefmt="unsafehtml")

        context["c"] = c  # this could be used for further options

        return TemplateResponse(request, "mainapp/page-sparql.html", context)


def debug_view(request, xyz=0):

    z = 1

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    return HttpResponse(f"Some plain message {xyz}")
