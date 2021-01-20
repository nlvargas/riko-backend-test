from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('apply', views.apply, name='apply'),
    path('chef_form', views.chefForm, name='chef_form'),
    path('terms', views.terms, name='terms'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)