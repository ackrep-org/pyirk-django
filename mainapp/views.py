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
    util.reload_data()

    context = dict(greeting_message="Hello, World!")

    return render(request, 'mainapp/landing-page.html', context)


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")

    payload = []
    if q:
        entities = Entity.objects.filter(Q(label__icontains=q) | Q(key_str__icontains=q))

        for idx, db_entity in enumerate(entities):
            db_entity: Entity

            payload.append(render_entity(db_entity, idx, script_tag="script"))

    return JsonResponse({"status": 200, "data": payload})


def render_entity(db_entity: Entity, idx, script_tag="myscript") -> str:
    template = get_template("mainapp/entity-list-entry.html")
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
    rendered_entity = render_entity(db_entity, idx=23, script_tag="script")
    context = dict(greeting_message="Hello, World!", rendered_entity=rendered_entity)

    return render(request, 'mainapp/searchresult-test-page.html', context)


def entity_view(request, key_str=None):
    db_entity = get_object_or_404(Entity, key_str=key_str)
    rendered_entity = render_entity(db_entity, idx=0, script_tag="myscript")
    rendered_entity_relations = render_entity_relations(db_entity)

    context = dict(
        rendered_entity=rendered_entity,
        entity=db_entity,
        rendered_entity_relations=rendered_entity_relations
    )
    return render(request, 'mainapp/entity-detail-page.html', context)


def render_entity_relations(db_entity: Entity) -> str:
    template = get_template("mainapp/entity-relations.html")

    # omit information which is already displayed by render_entity (label, description)
    black_listed_keys = ["R1", "R2"]

    relation_edges0 = pyerk.ds.relation_edges[db_entity.key_str]
    relation_edges = [re for re in relation_edges0 if re.relation.short_key not in black_listed_keys]

    ctx = {
        "relation_edges": relation_edges,
    }
    render_result = template.render(context=ctx)
    # IPS()
    return render_result


def debug_view(request, xyz=0):

    z = 1

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    return HttpResponse(f'Some plain message {xyz}')
