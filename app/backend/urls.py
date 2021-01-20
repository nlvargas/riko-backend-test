from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^', include('django.contrib.auth.urls')),
    path('api/', include('api.urls')),
    url(r'^admin/', admin.site.urls),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path('', include('web.urls')),
    url(r'^', include('django.contrib.auth.urls')),
    # path('api/', include('api.urls')),
    # prefix_default_language = True
)
