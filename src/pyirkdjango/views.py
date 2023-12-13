import os
from typing import Union, Optional, Dict, Tuple
import urllib
import json
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.template.loader import get_template
from django.views import View
from django.db.models import Q
from textwrap import dedent as twdd
from tabulate import tabulate
import pyirk
import pyirk.rdfstack
from . import util
from addict import Dict as attr_dict

from ipydex import IPS

from .models import Entity
from . import vis_integration


def home_page_view0(request):

    return HttpResponse("klappt")


def home_page_view(request):
    # util.reload_data_if_necessary()

    # this is a list of tuples like `[('irk:/ocse/0.2/math',  '/path/to/irk-data/ocse/math1.py'), ...],
    mods = list(pyirk.ds.mod_path_mapping.a.items())
    context = dict(loaded_pyirk_mods=mods)

    return render(request, "mainapp/page-landing.html", context)


def _entity_sort_key(entity) -> Tuple[str, int]:
    """
    Convert an short_key of an entity to a tuple which is used for sorting.

    (Reminder: second character is either a digit or "a" for autocreted items)

    "I25" -> ("I", 25)
    "I1200" -> ("I", 1200)      (should come after I25)
    "Ia1100" -> ("xI", 8234)    (auto-created items should come last)


    :param entity:
    :return:
    """

    uri = entity.uri
    mod_uri, sk = uri.split(pyirk.settings.URI_SEP)

    if sk[1].isdigit():
        num = int(sk[1:])
        letter = sk[0]
        # return
    else:
        num = int(sk[2:])
        letter = f"x{sk[0]}"

    return letter, num


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")
    # util.reload_data_if_necessary()

    payload = []
    if q:
        entities = Entity.objects.filter(
            Q(label__content__icontains=q) | Q(uri__icontains=q) | Q(description__icontains=q)
        )

        entity_list = list(entities)
        entity_list.sort(key=_entity_sort_key)

        for idx, db_entity in enumerate(entity_list):
            db_entity: Entity
            try:
                res = render_entity_inline(
                    db_entity, idx=idx, script_tag="script", include_description=True, highlight_text=q
                )
            except KeyError:
                # there seemse to be a bug related to data reloading and automatic key generation
                IPS()
                return JsonResponse({"status": 200, "data": []})
                raise

            payload.append(res)

    return JsonResponse({"status": 200, "data": payload})


def mockup(request):
    util.reload_data_if_necessary()
    db_entity = get_object_or_404(Entity, uri=pyirk.u("I5"))
    rendered_entity = render_entity_inline(db_entity, idx=23, script_tag="myscript", include_description=True)
    context = dict(greeting_message="Hello, World!", rendered_entity=rendered_entity)

    return render(request, "mainapp/page-mockup.html", context)


def entity_view(request, uri: Optional[str] = None, vis_options: Optional[Dict] = None):
    util.reload_data_if_necessary()
    # noinspection PyUnresolvedReferences
    uri = urllib.parse.unquote(uri)

    db_entity = get_object_or_404(Entity, uri=uri)
    rendered_entity = render_entity_inline(db_entity, special_class="highlight", include_description=True)
    rendered_entity_relations = render_entity_relations(db_entity)
    # rendered_entity_context_vars = render_entity_context_vars(db_entity)
    rendered_entity_scopes = render_entity_scopes(db_entity)

    rendered_vis_result = vis_integration.create_visualization(db_entity, vis_options)

    # TODO: This should be done in vis_integration.create_visualization;    bookmark://vis01
    #  or better: in visualize_entity() (called from there)
    if rendered_vis_result:
        rendered_vis_result = rendered_vis_result.replace(r"%", r"%25")

    context = dict(
        rendered_entity=rendered_entity,
        entity=db_entity,
        rendered_entity_relations=rendered_entity_relations,
        # rendered_entity_context_vars=rendered_entity_context_vars,
        rendered_entity_scopes=rendered_entity_scopes,
        rendered_vis_result=rendered_vis_result,
    )
    return render(request, "mainapp/page-entity-detail.html", context)


def entity_visualization_view(request, uri: Optional[str] = None):
    vis_dict = {"depth": 1}
    return entity_view(request, uri, vis_options=vis_dict)


def render_entity_inline(entity: Union[Entity, pyirk.Entity], **kwargs) -> str:

    # allow both models.Entity (from db) and "code-defined" pyirk.Entity
    if isinstance(entity, pyirk.Entity):
        code_entity = entity
    elif isinstance(entity, Entity):
        try:
            code_entity = pyirk.ds.get_entity_by_uri(entity.uri)
        except pyirk.auxiliary.UnknownURIError:
            # problematic: # irk:/ocse/0.2/zebra_puzzle_rules#I701

            #hack
            code_entity = pyirk.ds.get_entity_by_uri("irk:/builtins#I40")
            # IPS()
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
    uri = db_entity.uri

    # #########################################################################
    # frist: handle direct relations (where `db_entity` is subject)
    # #########################################################################

    # dict like {"R1": [<RelationEdge 1234>, ...], "R2": [...]}
    statements0 = pyirk.ds.statements[uri]

    # create a flat list of template-friendly dicts
    re_dict_2tuples = []
    for rel_key, re_list in statements0.items():
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
    inv_statements0 = pyirk.ds.inv_statements[uri]

    # create a flat list of template-friendly dicts
    inv_re_dict_2tuples = []
    for rel_key, inv_re_list in inv_statements0.items():
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
        "main_entity": {"special_class": "highlight", **represent_entity_as_dict(pyirk.ds.get_entity_by_uri(uri))},
        "re_dict_2tuples": re_dict_2tuples,
        "inv_re_dict_2tuples": inv_re_dict_2tuples,
    }
    template = get_template("mainapp/widget-entity-relations.html")
    render_result = template.render(context=ctx)

    return render_result


def render_entity_scopes(db_entity: Entity) -> str:
    code_entity = pyirk.ds.get_entity_by_uri(db_entity.uri)
    # noinspection PyProtectedMember

    scopes = pyirk.get_scopes(code_entity)

    scope_contents = []
    for scope in scopes:

        # #### first: handle "variables" (locally relevant items) defined in this scope

        items = pyirk.get_items_defined_in_scope(scope)
        re: pyirk.RelationEdge
        # currently we only use `R4__instance_of` as "defining relation"
        # statements = [re for key, re_list in statements0.items() if key not in black_listed_keys for re in re_list]
        defining_relation_triples = []
        for item in items:
            for re in pyirk.ds.statements[item.short_key]["R4"]:
                defining_relation_triples.append(list(map(represent_entity_as_dict, re.relation_tuple)))

        # #### second: handle further relation triples in this scope

        statement_relations = []
        re: pyirk.RelationEdge
        for re in pyirk.ds.scope_statements[scope.short_key]:
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


def represent_entity_as_dict(code_entity: Union[Entity, object]) -> dict:

    if isinstance(code_entity, pyirk.Entity):

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
            "detail_url": util.q_reverse("entitypage", uri=code_entity.uri),
            "template": "mainapp/widget-entity-inline.html",
            "_replacement_exceptions": _replacement_exceptions,
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
    util.unload_data(strict=False)
    util.reload_data_if_necessary(force=True)

    return HttpResponseRedirect(targeturl)


# this was taken from ackrep
class SearchSparqlView(View):
    # util.reload_data_if_necessary()

    def get(self, request):
        context = {}
        c = attr_dict()

        example_query = twdd(pyirk.rdfstack.get_sparql_example_query())
        qsrc = context["query"] = request.GET.get("query", example_query)

        try:
            tmp_results = pyirk.rdfstack.perform_sparql_query(qsrc)
            sparql_vars = [str(v) for v in tmp_results.vars]
            c.results = pyirk.aux.apply_func_to_table_cells(render_entity_inline, tmp_results)
        except pyirk.rdfstack.ParseException as e:
            context["err"] = f"The following error occurred: {type(e).__name__}: {str(e)}"
            c.results = []
            sparql_vars = []

        c.tab = tabulate(c.results, headers=sparql_vars, tablefmt="unsafehtml")

        context["c"] = c  # this could be used for further options

        return TemplateResponse(request, "mainapp/page-sparql.html", context)


class EditorView(View):

    def get(self, request, uri=None):

        c = context = attr_dict()
        if uri is None:
            uri2 = pyirk.ds.mod_path_mapping.b.get(settings.LC.IRK_DATA_MAIN_MOD)
        else:
            uri2 = urllib.parse.unquote(uri)

        c.fpath = pyirk.ds.mod_path_mapping.a.get(uri2)

        if not c.fpath:
            c.err = f"Invalid uri: `{uri2}` (parsed from uri-argument: `{uri}`)"
            return TemplateResponse(request, "mainapp/page-error.html", context)

        try:
            with open(c.fpath, "r") as fp:
                c.fcontent = fp.read()
            c.uri = uri2
        except FileNotFoundError as ex:
            c.err = str(ex)
            return TemplateResponse(request, "mainapp/page-error.html", context)

        return TemplateResponse(request, "mainapp/page-editor.html", context)


class ApiSaveFile(View):

    def get(self, request):

        context = attr_dict()
        if request.GET.get("success", None):
            context.msg = "file saved"
        else:
            context.msg = "something went wrong during saving"

        return JsonResponse({"status": 200, "data": context})

    def post(self, request):

        post_data = json.loads(request.body)
        file_content = post_data.get("editor_content")
        fpath = post_data.get("fpath")

        util.savetxt(fpath, file_content, backup=True)

        return HttpResponseRedirect(f"{request.path}?success=True")


# /api/get_auto_complete_list
def get_auto_complete_list(request):
    """
    Generate a list of strings which can be used in the auto-complete function of the web editor.
    This list consists mostly of short keys and indexed-keys and

    """
    all_entities = [*pyirk.ds.relations.values(), *pyirk.ds.items.values()]
    completion_suggestions = []
    for entity in all_entities:

        # TODO: implement a more elegant way to exclude auxiliary items
        if entity.short_key[1] == "a":
            continue

        completion_suggestions.append(entity.short_key)
        completion_suggestions.append(f'{entity.short_key}["{entity.R1}"]')
        if isinstance(entity, pyirk.Relation):
            underscore_r1 = entity.R1.replace(" ", "_")
            completion_suggestions.append(f"{entity.short_key}__{underscore_r1}")

    return JsonResponse({"status": 200, "data": completion_suggestions})


def debug_view(request, xyz=0):

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    txt = f"""
    {os.getcwd()}

    {pyirk.auxiliary.get_irk_root_dir()}
    """
    return HttpResponse(f"Some plain message {xyz}; {txt}")
