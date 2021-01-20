from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from .models import ChefForm
import json 


def index(request):
    return render(request, 'web/index.html')

def about(request):
    return render(request, 'web/about.html')

def apply(request):
    return render(request, 'web/apply.html')

def terms(request):
    try:
        return FileResponse(open('web/docs/terms_and_conditions.pdf', 'rb'), content_type='application/pdf')
    except FileNotFoundError:
        raise Http404()

@csrf_exempt
def chefForm(request):
    data = request.POST.dict()
    chef_form = ChefForm.objects.create(fullname=data["fullname"],
                                        contactInfo=data["contactInfo"],
                                        city=data["city"],
                                        commune=data["commune"],
                                        message=data["message"])
    chef_form.save()
    return render(request, 'web/apply.html')
