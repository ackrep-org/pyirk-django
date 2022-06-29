import os
import json
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.conf import settings

from ipydex import IPS

from .models import Item


def generate_data():

    data = [
        'I1("General Item")',
        'I2("Metaclass")',
        'I3("Field of science")',
        'I4("Mathematics")',
        'I5("Engineering")',
        'I6("mathematical operation")',
        'I7("mathematical operation with arity 1")',
        'I8("mathematical operation with arity 2")',
        'I9("mathematical operation with arity 3")',
    ]

    for txt in data:
        Item.objects.create(label=txt)



def home_page_view(request, form_data_len=None):

    # generate_data()


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
