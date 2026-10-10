from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .actors import get_recipe_actor
from .forms import (
    IngredientGroupFormSet,
    RecipeForm,
    RecipeImageFormSet,
    RecipeIngredientFormSet,
    RecipeNoteForm,
    RecipeStepFormSet,
)
from .models import Category, IngredientGroup, Recipe, RecipeImage, RecipeIngredient, RecipeNote


_TRANSLITERATION = str.maketrans({
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'yo',
    'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'j', 'К': 'k', 'Л': 'l', 'М': 'm',
    'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
    'Ф': 'f', 'Х': 'h', 'Ц': 'c', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'shch', 'Ъ': '',
    'Ы': 'y', 'Ь': '', 'Э': 'e', 'Ю': 'yu', 'Я': 'ya',
})


def home(request):
    return render(request, 'index.html')


def _can_manage_recipes(request):
    try:
        get_recipe_actor(request)
    except PermissionDenied:
        return False
    return True


CATALOG_TIME_CHOICES = (
    ('30', 'до 30 мин'),
    ('60', 'до 60 мин'),
    ('90', 'до 90 мин'),
)
CATALOG_SORT_CHOICES = (
    ('new', 'Сначала новые'),
    ('title', 'По алфавиту'),
    ('-title', 'По алфавиту Я–А'),
    ('-rating', 'По рейтингу'),
    ('time', 'Сначала быстрые'),
)
CATALOG_SORTING = {
    'new': ('-published_at', '-created_at', '-id'),
    'title': ('title', 'id'),
    '-title': ('-title', '-id'),
    '-rating': ('-rating', 'title', 'id'),
    'time': ('total_time', 'title', 'id'),
}


def _catalog_product_values(request):
    values = []
    for raw_value in request.GET.getlist('product'):
        values.extend(raw_value.split(','))
    return list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))


def _catalog_rating(value):
    if not value:
        return None
    try:
        rating = Decimal(value)
    except InvalidOperation:
        return None
    return rating if Decimal('1') <= rating <= Decimal('5') else None


def _catalog_queryset(request, *, can_manage_recipes, category_slugs, product_values, time_value, difficulty, rating, sort):
    queryset = Recipe.objects.all() if can_manage_recipes else Recipe.objects.filter(
        publication_status=Recipe.PublicationStatus.PUBLISHED
    )
    queryset = queryset.annotate(total_time=F('prep_minutes') + F('cook_minutes'))

    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(ingredients__product__name__icontains=query)
        )

    if category_slugs:
        queryset = queryset.filter(categories__slug__in=category_slugs)

    for product_value in product_values:
        queryset = queryset.filter(ingredients__product__normalized_name=product_value)

    if time_value:
        queryset = queryset.filter(total_time__lte=int(time_value))
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    if rating is not None:
        queryset = queryset.filter(rating__gte=rating)

    return (
        queryset.distinct()
        .select_related('created_by')
        .prefetch_related(
            'categories',
            Prefetch(
                'images',
                queryset=RecipeImage.objects.filter(is_cover=True).only(
                    'id', 'recipe_id', 'image', 'alt_text', 'sort_order', 'is_cover'
                ),
                to_attr='cover_images',
            ),
        )
        .order_by(*CATALOG_SORTING[sort])
    )


def recipe_list(request):
    can_manage_recipes = _can_manage_recipes(request)
    categories = list(Category.objects.select_related('parent').all())
    valid_category_slugs = {category.slug for category in categories}
    category_slugs = list(
        dict.fromkeys(
            slug for slug in request.GET.getlist('category') if slug in valid_category_slugs
        )
    )
    product_values = _catalog_product_values(request)
    time_values = {value for value, _ in CATALOG_TIME_CHOICES}
    time_value = request.GET.get('time', '')
    if time_value not in time_values:
        time_value = ''
    difficulty_values = {value for value, _ in Recipe.Difficulty.choices}
    difficulty = request.GET.get('difficulty', '')
    if difficulty not in difficulty_values:
        difficulty = ''
    rating = _catalog_rating(request.GET.get('rating', ''))
    sort_values = {value for value, _ in CATALOG_SORT_CHOICES}
    sort = request.GET.get('sort', 'new')
    if sort not in sort_values:
        sort = 'new'

    queryset = _catalog_queryset(
        request,
        can_manage_recipes=can_manage_recipes,
        category_slugs=category_slugs,
        product_values=product_values,
        time_value=time_value,
        difficulty=difficulty,
        rating=rating,
        sort=sort,
    )
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    active_filter_count = len(category_slugs) + len(product_values)
    active_filter_count += int(bool(time_value)) + int(bool(difficulty)) + int(rating is not None)

    return render(
        request,
        'recipes.html',
        {
            'can_manage_recipes': can_manage_recipes,
            'categories': categories,
            'page_obj': page_obj,
            'recipes': page_obj.object_list,
            'query': request.GET.get('q', '').strip(),
            'selected_category_slugs': set(category_slugs),
            'product_values': product_values,
            'product_query': ', '.join(product_values),
            'time_value': time_value,
            'difficulty': difficulty,
            'rating_value': rating,
            'sort': sort,
            'time_choices': CATALOG_TIME_CHOICES,
            'sort_choices': CATALOG_SORT_CHOICES,
            'active_filter_count': active_filter_count,
            'has_active_filters': bool(active_filter_count),
            'query_string': query_params.urlencode(),
        },
    )


def _recipe_detail_queryset():
    ingredient_queryset = RecipeIngredient.objects.select_related('product', 'unit')
    group_queryset = IngredientGroup.objects.prefetch_related(
        Prefetch('ingredients', queryset=ingredient_queryset)
    )
    return (
        Recipe.objects.select_related('created_by')
        .prefetch_related(
            'categories',
            Prefetch('images', queryset=RecipeImage.objects.all()),
            Prefetch('ingredient_groups', queryset=group_queryset),
            'steps',
            Prefetch('notes', queryset=RecipeNote.objects.select_related('author')),
        )
    )


def _get_published_recipe(slug):
    return get_object_or_404(
        Recipe.objects.filter(publication_status=Recipe.PublicationStatus.PUBLISHED),
        slug=slug,
    )


def _get_recipe_for_detail(request, slug):
    recipe = get_object_or_404(_recipe_detail_queryset(), slug=slug)
    if recipe.publication_status == Recipe.PublicationStatus.PUBLISHED:
        return recipe
    if _can_manage_recipes(request):
        return recipe
    raise Http404


def _get_recipe_for_management(request, slug):
    actor = get_recipe_actor(request)
    recipe = get_object_or_404(Recipe, slug=slug)
    return recipe, actor


def _unique_recipe_slug(title):
    base_slug = slugify(title.translate(_TRANSLITERATION)) or 'recipe'
    slug = base_slug
    suffix = 2
    while Recipe.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{suffix}'
        suffix += 1
    return slug


def _build_formsets(recipe, data=None, files=None):
    formsets = {
        'group_formset': IngredientGroupFormSet(data, files, instance=recipe, prefix='groups'),
        'ingredient_formset': RecipeIngredientFormSet(data, files, instance=recipe, prefix='ingredients'),
        'step_formset': RecipeStepFormSet(data, files, instance=recipe, prefix='steps'),
        'image_formset': RecipeImageFormSet(data, files, instance=recipe, prefix='images'),
    }
    group_queryset = IngredientGroup.objects.filter(recipe=recipe) if recipe.pk else IngredientGroup.objects.none()
    for ingredient_form in formsets['ingredient_formset'].forms:
        ingredient_form.fields['group'].queryset = group_queryset
    return formsets


def _normalise_deleted_ingredient_groups(group_formset, ingredient_formset):
    deleted_group_ids = {
        form.instance.pk
        for form in group_formset.forms
        if form.cleaned_data.get('DELETE', False) and form.instance.pk
    }
    if not deleted_group_ids:
        return

    for form in ingredient_formset.forms:
        if not form.cleaned_data or form.cleaned_data.get('DELETE', False):
            continue
        group = form.cleaned_data.get('group')
        if group and group.pk in deleted_group_ids:
            form.cleaned_data['group'] = None
            form.instance.group = None


def _save_recipe_and_related(recipe_form, formsets, *, actor=None, is_create=False):
    with transaction.atomic():
        recipe = recipe_form.save(commit=False)
        if is_create:
            recipe.created_by = actor
            recipe.slug = _unique_recipe_slug(recipe.title)
        if recipe.publication_status == Recipe.PublicationStatus.PUBLISHED and recipe.published_at is None:
            recipe.published_at = timezone.now()
        recipe.save()
        recipe_form.save_m2m()

        for formset in formsets.values():
            formset.instance = recipe

        _normalise_deleted_ingredient_groups(
            formsets['group_formset'], formsets['ingredient_formset']
        )
        formsets['ingredient_formset'].save()
        formsets['group_formset'].save()
        formsets['step_formset'].save()
        formsets['image_formset'].save()
    return recipe


def _recipe_form_context(recipe_form, formsets, *, recipe=None):
    return {
        'recipe_form': recipe_form,
        **formsets,
        'recipe': recipe,
        'is_edit': recipe is not None,
    }


def recipe_create(request):
    actor = get_recipe_actor(request)
    recipe = Recipe()
    if request.method == 'POST':
        recipe_form = RecipeForm(request.POST)
        formsets = _build_formsets(recipe, request.POST, request.FILES)
        all_valid = recipe_form.is_valid()
        formsets_valid = [formset.is_valid() for formset in formsets.values()]
        if all_valid and all(formsets_valid):
            recipe = _save_recipe_and_related(recipe_form, formsets, actor=actor, is_create=True)
            return redirect(recipe)
    else:
        recipe_form = RecipeForm()
        formsets = _build_formsets(recipe)
    return render(request, 'recipes/recipe_form.html', _recipe_form_context(recipe_form, formsets))


def recipe_edit(request, slug):
    recipe, _ = _get_recipe_for_management(request, slug)
    if request.method == 'POST':
        recipe_form = RecipeForm(request.POST, instance=recipe)
        formsets = _build_formsets(recipe, request.POST, request.FILES)
        all_valid = recipe_form.is_valid()
        formsets_valid = [formset.is_valid() for formset in formsets.values()]
        if all_valid and all(formsets_valid):
            recipe = _save_recipe_and_related(recipe_form, formsets)
            return redirect(recipe)
    else:
        recipe_form = RecipeForm(instance=recipe)
        formsets = _build_formsets(recipe)
    return render(request, 'recipes/recipe_form.html', _recipe_form_context(recipe_form, formsets, recipe=recipe))


def recipe_detail(request, slug):
    recipe = _get_recipe_for_detail(request, slug)
    cover_image = next((image for image in recipe.images.all() if image.is_cover), None)
    return render(
        request,
        'recipe.html',
        {
            'recipe': recipe,
            'cover_image': cover_image,
            'can_manage_recipes': _can_manage_recipes(request),
        },
    )


@require_POST
def recipe_delete(request, slug):
    recipe, _ = _get_recipe_for_management(request, slug)
    recipe.delete()
    return redirect('recipes:recipe_list')


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