from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from .models import IngredientGroup, Recipe, RecipeIngredient, RecipeNote, RecipeImage


def home(request):
    return render(request, 'index.html')


def recipe_list(request):
    return render(request, 'recipes.html')


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
