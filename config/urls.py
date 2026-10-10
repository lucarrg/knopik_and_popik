from django.contrib import admin
from django.urls import include, path

from recipes import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('recipes/', include('recipes.urls')),
]
