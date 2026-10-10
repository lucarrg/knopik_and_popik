from django.urls import path

from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('<slug:slug>/', views.recipe_detail, name='recipe_detail'),
    path('<slug:slug>/notes/add/', views.recipe_note_add, name='recipe_note_add'),
    path('<slug:slug>/notes/<int:note_id>/edit/', views.recipe_note_edit, name='recipe_note_edit'),
    path('<slug:slug>/notes/<int:note_id>/delete/', views.recipe_note_delete, name='recipe_note_delete'),
]
