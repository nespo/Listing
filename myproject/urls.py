from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from myapp.views import form_field_setting_changelist

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/formfieldsetting/', form_field_setting_changelist, name='formfieldsetting_changelist'),
    path('', include('myapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
