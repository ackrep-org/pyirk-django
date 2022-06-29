from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
import pyerk

from ipydex import IPS

from .models import Item


def reload_data():

    # delete all existing data
    Item.objects.all().delete()

    mod = pyerk.erkloader.load_mod_from_path("../controltheory_experiments/knowledge_base1.py", "knowledge_base1")

    data = [repr(itm) for itm in pyerk.ds.items.values()]

    for txt in data:
        Item.objects.create(label=txt)


def home_page_view(request, form_data_len=None):

    # generate_data()

    reload_data()

    context = dict(greeting_message="Hello, World!")

    return render(request, 'mainapp/main.html', context)


# /search/?q=...
def get_item(request):

    q = request.GET.get("q")

    payload = []
    if q:
        items = Item.objects.filter(label__icontains=q)

        for item in items:
            payload.append(str(item))

    return JsonResponse({"status": 200, "data": payload})


def debug_view(request, xyz=0):

    z = 1

    if xyz == 1:
        # start interactive shell for debugging (helpful if called from the unittests)
        IPS()

    elif xyz == 2:
        return HttpResponseServerError("Errormessage")

    return HttpResponse('Some plain message')
