from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .actors import get_recipe_actor
from .forms import RecipeNoteForm
from .models import IngredientGroup, Recipe, RecipeImage, RecipeIngredient, RecipeNote


def home(request):
    return render(request, 'index.html')


def recipe_list(request):
    return render(request, 'recipes.html')


def _get_published_recipe(slug):
    return get_object_or_404(
        Recipe.objects.filter(publication_status=Recipe.PublicationStatus.PUBLISHED),
        slug=slug,
    )


def recipe_detail(request, slug):
    ingredient_queryset = RecipeIngredient.objects.select_related('product', 'unit')
    group_queryset = IngredientGroup.objects.prefetch_related(
        Prefetch('ingredients', queryset=ingredient_queryset)
    )
    recipe = get_object_or_404(
        Recipe.objects.filter(publication_status=Recipe.PublicationStatus.PUBLISHED)
        .select_related('created_by')
        .prefetch_related(
            'categories',
            Prefetch('images', queryset=RecipeImage.objects.all()),
            Prefetch('ingredient_groups', queryset=group_queryset),
            'steps',
            Prefetch('notes', queryset=RecipeNote.objects.select_related('author')),
        ),
        slug=slug,
    )
    cover_image = next((image for image in recipe.images.all() if image.is_cover), None)
    return render(request, 'recipe.html', {'recipe': recipe, 'cover_image': cover_image})


@require_POST
def recipe_note_add(request, slug):
    recipe = _get_published_recipe(slug)
    actor = get_recipe_actor(request)
    form = RecipeNoteForm(request.POST)
    if form.is_valid():
        RecipeNote.objects.create(recipe=recipe, author=actor, text=form.cleaned_data['text'])
    return redirect(recipe)


@require_POST
def recipe_note_edit(request, slug, note_id):
    recipe = _get_published_recipe(slug)
    get_recipe_actor(request)
    note = get_object_or_404(RecipeNote, pk=note_id, recipe=recipe)
    form = RecipeNoteForm(request.POST)
    if form.is_valid():
        note.text = form.cleaned_data['text']
        note.save(update_fields=['text', 'updated_at'])
    return redirect(recipe)


@require_POST
def recipe_note_delete(request, slug, note_id):
    recipe = _get_published_recipe(slug)
    get_recipe_actor(request)
    note = get_object_or_404(RecipeNote, pk=note_id, recipe=recipe)
    note.delete()
    return redirect(recipe)
