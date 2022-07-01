from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
import pyerk

from ipydex import IPS

from .models import Item


def reload_data():

    # delete all existing data
    Item.objects.all().delete()

    mod = pyerk.erkloader.load_mod_from_path("../controltheory_experiments/knowledge_base1.py", "knowledge_base1")

    for itm in pyerk.ds.items.values():
        Item.objects.create(
            key_str=itm.short_key,
            label=getattr(itm, "R1", None),
            description=getattr(itm, "R2", None),
        )


def home_page_view(request):

    # TODO: in the future this should not be triggered on every page refresh
    reload_data()

    context = dict(greeting_message="Hello, World!")

    return render(request, 'mainapp/main.html', context)


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")
    template = get_template("mainapp/entity-list-entry.html")

    payload = []
    if q:
        items = Item.objects.filter(label__icontains=q)

        for db_item in items:
            db_item: Item
            ctx = {
                "key_str": db_item.key_str,
                "label": db_item.label,
                "description": db_item.description,
            }
            rendered_item = template.render(context=ctx)
            payload.append(rendered_item)

    return JsonResponse({"status": 200, "data": payload})


def mockup(request):

    # TODO: in the future this should not be triggered on every page refresh
    # reload_data()

    context = dict(greeting_message="Hello, World!")

    return render(request, 'mainapp/searchresult-test.html', context)


def debug_view(request, xyz=0):

    z = 1

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    return HttpResponse('Some plain message')
