from django.urls import path

from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('create/', views.recipe_create, name='recipe_create'),
    path('<slug:slug>/edit/', views.recipe_edit, name='recipe_edit'),
    path('<slug:slug>/delete/', views.recipe_delete, name='recipe_delete'),
    path('<slug:slug>/notes/add/', views.recipe_note_add, name='recipe_note_add'),
    path('<slug:slug>/notes/<int:note_id>/edit/', views.recipe_note_edit, name='recipe_note_edit'),
    path('<slug:slug>/notes/<int:note_id>/delete/', views.recipe_note_delete, name='recipe_note_delete'),
    path('<slug:slug>/', views.recipe_detail, name='recipe_detail'),
]