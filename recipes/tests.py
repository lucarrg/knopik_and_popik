from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .actors import get_recipe_actor
from .forms import RecipeImageFormSet
from .models import Category, Product, Recipe, RecipeImage, RecipeIngredient, RecipeNote, Unit


class RecipeDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_recipe')
        cls.recipe = Recipe.objects.get(slug='orzo-s-lososem')

    def test_total_minutes(self):
        self.assertEqual(self.recipe.total_minutes, 45)

    def test_get_absolute_url(self):
        self.assertEqual(self.recipe.get_absolute_url(), '/recipes/orzo-s-lososem/')

    def test_published_recipe_detail_renders_database_content(self):
        response = self.client.get(self.recipe.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.recipe.title)
        self.assertContains(response, 'Основные блюда')
        self.assertContains(response, 'Лосось')
        self.assertContains(response, 'Подготовьте продукты')
        self.assertContains(response, 'Проверено')

    def test_unknown_recipe_slug_returns_404(self):
        response = self.client.get('/recipes/missing-recipe/')
        self.assertEqual(response.status_code, 404)

    def test_seed_command_is_idempotent(self):
        call_command('seed_demo_recipe')
        self.assertEqual(Recipe.objects.filter(slug='orzo-s-lososem').count(), 1)
        self.assertEqual(self.recipe.categories.count(), 2)
        self.assertEqual(self.recipe.ingredients.count(), 11)
        self.assertEqual(self.recipe.steps.count(), 4)
        self.assertEqual(self.recipe.notes.count(), 1)

@override_settings(DEBUG=True)
class RecipeNoteCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_recipe')
        cls.recipe = Recipe.objects.get(slug='orzo-s-lososem')
        cls.actor = get_user_model().objects.get(username='masha-demo')
        cls.other_user = get_user_model().objects.create_user(
            username='other-user',
            password='test-password',
        )
        cls.other_recipe = Recipe.objects.create(
            title='Другой рецепт',
            slug='other-recipe',
            description='Тестовый рецепт для проверки границ доступа.',
            base_servings=2,
            prep_minutes=5,
            cook_minutes=10,
            difficulty=Recipe.Difficulty.EASY,
            publication_status=Recipe.PublicationStatus.PUBLISHED,
            created_by=cls.actor,
        )
        cls.other_note = RecipeNote.objects.create(
            recipe=cls.other_recipe,
            author=cls.other_user,
            text='Заметка другого рецепта.',
        )

    def add_url(self):
        return reverse('recipes:recipe_note_add', args=[self.recipe.slug])

    def edit_url(self, note):
        return reverse('recipes:recipe_note_edit', args=[self.recipe.slug, note.pk])

    def delete_url(self, note):
        return reverse('recipes:recipe_note_delete', args=[self.recipe.slug, note.pk])

    def test_add_note_creates_note_for_debug_actor_and_redirects(self):
        response = self.client.post(
            self.add_url(),
            {'text': '  Новая серверная заметка.  ', 'author': self.other_user.pk, 'recipe': self.other_recipe.pk},
        )

        self.assertRedirects(response, self.recipe.get_absolute_url(), fetch_redirect_response=False)
        note = RecipeNote.objects.get(recipe=self.recipe, text='Новая серверная заметка.')
        self.assertEqual(note.author, self.actor)

    def test_blank_note_does_not_create_record(self):
        initial_count = RecipeNote.objects.filter(recipe=self.recipe).count()

        response = self.client.post(self.add_url(), {'text': '   '})

        self.assertRedirects(response, self.recipe.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(RecipeNote.objects.filter(recipe=self.recipe).count(), initial_count)

    def test_edit_note_updates_text_but_cannot_override_author(self):
        note = RecipeNote.objects.filter(recipe=self.recipe).first()

        response = self.client.post(
            self.edit_url(note),
            {'text': '  Обновлённый текст.  ', 'author': self.other_user.pk, 'recipe': self.other_recipe.pk},
        )

        self.assertRedirects(response, self.recipe.get_absolute_url(), fetch_redirect_response=False)
        note.refresh_from_db()
        self.assertEqual(note.text, 'Обновлённый текст.')
        self.assertEqual(note.author, self.actor)

    def test_delete_note_removes_only_target_note(self):
        note = RecipeNote.objects.filter(recipe=self.recipe).first()
        other_note_pk = self.other_note.pk

        response = self.client.post(self.delete_url(note))

        self.assertRedirects(response, self.recipe.get_absolute_url(), fetch_redirect_response=False)
        self.assertFalse(RecipeNote.objects.filter(pk=note.pk).exists())
        self.assertTrue(RecipeNote.objects.filter(pk=other_note_pk).exists())

    def test_get_delete_returns_405(self):
        note = RecipeNote.objects.filter(recipe=self.recipe).first()

        response = self.client.get(self.delete_url(note))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(RecipeNote.objects.filter(pk=note.pk).exists())

    def test_get_edit_returns_405(self):
        note = RecipeNote.objects.filter(recipe=self.recipe).first()
        original_text = note.text

        response = self.client.get(self.edit_url(note))

        self.assertEqual(response.status_code, 405)
        note.refresh_from_db()
        self.assertEqual(note.text, original_text)

    def test_note_from_another_recipe_cannot_be_edited_or_deleted(self):
        edit_response = self.client.post(
            reverse('recipes:recipe_note_edit', args=[self.recipe.slug, self.other_note.pk]),
            {'text': 'Попытка изменить чужую заметку.'},
        )
        delete_response = self.client.post(
            reverse('recipes:recipe_note_delete', args=[self.recipe.slug, self.other_note.pk]),
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.other_note.refresh_from_db()
        self.assertEqual(self.other_note.text, 'Заметка другого рецепта.')

    def test_detail_page_renders_saved_note(self):
        RecipeNote.objects.create(
            recipe=self.recipe,
            author=self.actor,
            text='Заметка, сохранённая в базе данных.',
        )

        response = self.client.get(self.recipe.get_absolute_url())

        self.assertContains(response, 'Заметка, сохранённая в базе данных.')
        self.assertContains(response, 'Маша')

    @override_settings(DEBUG=True)
    def test_debug_mode_uses_masha_demo_as_actor(self):
        request = RequestFactory().post('/')
        request.user = AnonymousUser()

        self.assertEqual(get_recipe_actor(request), self.actor)

@override_settings(DEBUG=True)
class RecipeCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_recipe')
        cls.actor = get_user_model().objects.get(username='masha-demo')
        cls.other_user = get_user_model().objects.create_user(
            username='another-owner', password='test-password'
        )
        cls.categories = list(Category.objects.filter(slug__in=['osnovnye-blyuda', 'ryba']))
        cls.gram = Unit.objects.get(abbreviation='г')

    def formset_management(self, prefix, total=0, initial=0):
        return {
            f'{prefix}-TOTAL_FORMS': str(total),
            f'{prefix}-INITIAL_FORMS': str(initial),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }

    def recipe_payload(self, **overrides):
        payload = {
            'title': 'Тестовый рецепт',
            'description': 'Описание тестового рецепта.',
            'publication_status': Recipe.PublicationStatus.PUBLISHED,
            'recipe_status': Recipe.RecipeStatus.VERIFIED,
            'base_servings': '4',
            'prep_minutes': '10',
            'cook_minutes': '20',
            'difficulty': Recipe.Difficulty.EASY,
            'rating': '4.5',
            'source_url': '',
            'categories': [str(category.pk) for category in self.categories],
        }
        payload.update(self.formset_management('groups'))
        payload.update(self.formset_management('ingredients'))
        payload.update(self.formset_management('steps'))
        payload.update(self.formset_management('images'))
        payload.update(overrides)
        return payload

    def create_url(self):
        return reverse('recipes:recipe_create')

    def create_recipe(self, **overrides):
        response = self.client.post(self.create_url(), self.recipe_payload(**overrides))
        self.assertEqual(response.status_code, 302, response.content.decode())
        return Recipe.objects.filter(title=overrides.get('title', 'Тестовый рецепт')).latest('pk')

    def test_create_recipe_sets_actor_generates_slug_and_saves_categories(self):
        recipe = self.create_recipe(created_by=self.other_user.pk)

        self.assertEqual(recipe.created_by, self.actor)
        self.assertEqual(recipe.slug, 'testovyj-recept')
        self.assertSetEqual(set(recipe.categories.all()), set(self.categories))
        self.assertEqual(self.client.get(recipe.get_absolute_url()).status_code, 200)

    def test_slug_gets_incrementing_suffix(self):
        Recipe.objects.create(
            title='Тестовый рецепт', slug='testovyj-recept', description='Первый.',
            base_servings=1, prep_minutes=0, cook_minutes=0,
            difficulty=Recipe.Difficulty.EASY, created_by=self.actor,
        )
        recipe = self.create_recipe()

        self.assertEqual(recipe.slug, 'testovyj-recept-2')

    def test_create_saves_ingredients_creates_and_reuses_products(self):
        existing = Product.objects.create(name='Кускус')
        payload = self.recipe_payload()
        payload.update(self.formset_management('ingredients', total=3))
        payload.update({
            'ingredients-0-product_name': 'Новый продукт',
            'ingredients-0-group': '',
            'ingredients-0-quantity': '100',
            'ingredients-0-unit': str(self.gram.pk),
            'ingredients-0-note': '',
            'ingredients-0-sort_order': '0',
            'ingredients-1-product_name': 'Кускус',
            'ingredients-1-group': '',
            'ingredients-1-quantity': '120',
            'ingredients-1-unit': str(self.gram.pk),
            'ingredients-1-note': '',
            'ingredients-1-sort_order': '1',
            'ingredients-2-product_name': 'Соль',
            'ingredients-2-group': '',
            'ingredients-2-quantity': '',
            'ingredients-2-unit': '',
            'ingredients-2-note': 'по вкусу',
            'ingredients-2-sort_order': '2',
        })

        response = self.client.post(self.create_url(), payload)
        self.assertEqual(response.status_code, 302, response.content.decode())
        recipe = Recipe.objects.get(title='Тестовый рецепт')
        self.assertEqual(recipe.ingredients.count(), 3)
        self.assertEqual(recipe.ingredients.get(product__normalized_name='новый продукт').quantity, 100)
        self.assertEqual(recipe.ingredients.get(product=existing).quantity, 120)
        to_taste = recipe.ingredients.get(product__normalized_name='соль')
        self.assertIsNone(to_taste.quantity)
        self.assertIsNone(to_taste.unit)
        self.assertEqual(to_taste.note, 'по вкусу')

    def test_create_saves_steps(self):
        payload = self.recipe_payload()
        payload.update(self.formset_management('steps', total=2))
        payload.update({
            'steps-0-title': 'Первый шаг', 'steps-0-text': 'Сделайте первое действие.', 'steps-0-sort_order': '0',
            'steps-1-title': 'Второй шаг', 'steps-1-text': 'Сделайте второе действие.', 'steps-1-sort_order': '1',
        })

        response = self.client.post(self.create_url(), payload)
        self.assertEqual(response.status_code, 302, response.content.decode())
        recipe = Recipe.objects.get(title='Тестовый рецепт')
        self.assertEqual(list(recipe.steps.values_list('title', flat=True)), ['Первый шаг', 'Второй шаг'])

    def test_image_formset_rejects_multiple_cover_images(self):
        recipe = Recipe.objects.create(
            title='Для обложек', slug='for-covers', description='Тест.', base_servings=1,
            prep_minutes=0, cook_minutes=0, difficulty=Recipe.Difficulty.EASY, created_by=self.actor,
        )
        image_bytes = (
            b'GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        data = self.formset_management('images', total=2)
        data.update({
            'images-0-alt_text': 'Первая', 'images-0-sort_order': '0', 'images-0-is_cover': 'on',
            'images-1-alt_text': 'Вторая', 'images-1-sort_order': '1', 'images-1-is_cover': 'on',
        })
        files = {
            'images-0-image': SimpleUploadedFile('first.gif', image_bytes, content_type='image/gif'),
            'images-1-image': SimpleUploadedFile('second.gif', image_bytes, content_type='image/gif'),
        }

        formset = RecipeImageFormSet(data, files, instance=recipe, prefix='images')
        self.assertFalse(formset.is_valid())
        self.assertIn('только одна обложка', str(formset.non_form_errors()))

    def test_edit_changes_fields_without_changing_slug(self):
        recipe = Recipe.objects.create(
            title='До изменения', slug='stable-slug', description='До.', base_servings=2,
            prep_minutes=5, cook_minutes=10, difficulty=Recipe.Difficulty.EASY, created_by=self.actor,
        )
        payload = self.recipe_payload(
            title='После изменения', description='После.', prep_minutes='25', categories=[]
        )

        response = self.client.post(reverse('recipes:recipe_edit', args=[recipe.slug]), payload)
        self.assertRedirects(response, recipe.get_absolute_url(), fetch_redirect_response=False)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, 'После изменения')
        self.assertEqual(recipe.prep_minutes, 25)
        self.assertEqual(recipe.slug, 'stable-slug')

    def test_deleting_group_sets_linked_ingredients_group_to_none(self):
        recipe = Recipe.objects.get(slug='orzo-s-lososem')
        group = recipe.ingredient_groups.first()
        ingredient = recipe.ingredients.first()
        payload = self.recipe_payload(
            title=recipe.title, description=recipe.description, base_servings=str(recipe.base_servings),
            prep_minutes=str(recipe.prep_minutes), cook_minutes=str(recipe.cook_minutes),
            difficulty=recipe.difficulty, publication_status=recipe.publication_status,
            recipe_status=recipe.recipe_status, rating=str(recipe.rating), categories=[str(c.pk) for c in recipe.categories.all()],
        )
        payload.update(self.formset_management('groups', total=1, initial=1))
        payload.update({'groups-0-id': str(group.pk), 'groups-0-name': group.name, 'groups-0-sort_order': str(group.sort_order), 'groups-0-DELETE': 'on'})
        ingredients = list(recipe.ingredients.all())
        payload.update(self.formset_management('ingredients', total=len(ingredients), initial=len(ingredients)))
        for index, current in enumerate(ingredients):
            payload.update({
                f'ingredients-{index}-id': str(current.pk), f'ingredients-{index}-product_name': current.product.name,
                f'ingredients-{index}-group': str(current.group_id or ''), f'ingredients-{index}-quantity': str(current.quantity or ''),
                f'ingredients-{index}-unit': str(current.unit_id or ''), f'ingredients-{index}-note': current.note,
                f'ingredients-{index}-sort_order': str(current.sort_order),
            })
        payload.update(self.formset_management('steps', total=0))
        payload.update(self.formset_management('images', total=0))

        response = self.client.post(reverse('recipes:recipe_edit', args=[recipe.slug]), payload)
        self.assertEqual(response.status_code, 302, response.content.decode())
        ingredient.refresh_from_db()
        self.assertIsNone(ingredient.group)

    def test_delete_recipe_requires_post_and_post_deletes(self):
        recipe = Recipe.objects.create(
            title='Удаляемый', slug='delete-me', description='Тест.', base_servings=1,
            prep_minutes=0, cook_minutes=0, difficulty=Recipe.Difficulty.EASY, created_by=self.actor,
        )
        url = reverse('recipes:recipe_delete', args=[recipe.slug])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())
        response = self.client.post(url)
        self.assertRedirects(response, reverse('recipes:recipe_list'), fetch_redirect_response=False)
        self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_invalid_step_formset_rolls_back_recipe_creation(self):
        payload = self.recipe_payload(title='Не должен сохраниться')
        payload.update(self.formset_management('steps', total=1))
        payload.update({'steps-0-title': 'Есть заголовок', 'steps-0-text': '', 'steps-0-sort_order': '0'})

        response = self.client.post(self.create_url(), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Recipe.objects.filter(title='Не должен сохраниться').exists())

    @override_settings(DEBUG=False)
    def test_production_anonymous_cannot_mutate_and_cannot_view_draft(self):
        draft = Recipe.objects.create(
            title='Черновик', slug='private-draft', description='Черновик.', base_servings=1,
            prep_minutes=0, cook_minutes=0, difficulty=Recipe.Difficulty.EASY,
            publication_status=Recipe.PublicationStatus.DRAFT, created_by=self.actor,
        )
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(self.create_url(), self.recipe_payload()).status_code, 403)
        self.assertEqual(self.client.post(reverse('recipes:recipe_edit', args=[draft.slug]), self.recipe_payload()).status_code, 403)

    @override_settings(DEBUG=False)
    def test_authenticated_owner_can_view_draft(self):
        draft = Recipe.objects.create(
            title='Черновик владельца', slug='owner-draft', description='Черновик.', base_servings=1,
            prep_minutes=0, cook_minutes=0, difficulty=Recipe.Difficulty.EASY,
            publication_status=Recipe.PublicationStatus.DRAFT, created_by=self.actor,
        )
        self.client.force_login(self.actor)

        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 200)

@override_settings(DEBUG=False)
class RecipeCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_recipe')
        cls.actor = get_user_model().objects.get(username='masha-demo')
        cls.main_category = Category.objects.get(slug='osnovnye-blyuda')
        cls.fish_category = Category.objects.get(slug='ryba')
        cls.breakfast_category = Category.objects.create(name='Завтраки', slug='zavtraki')
        cls.salmon = cls.product('Лосось')
        cls.lemon = cls.product('Лимон')
        cls.chicken = cls.product('Курица')
        cls.fast_recipe = cls.make_recipe(
            'Быстрый лимонный завтрак', 'fast-lemon-breakfast',
            'Быстрое блюдо с ярким лимонным вкусом.', [cls.breakfast_category],
            [cls.lemon], prep=5, cook=10, difficulty=Recipe.Difficulty.EASY, rating='4.0',
        )
        cls.combo_recipe = cls.make_recipe(
            'Лосось с лимоном', 'salmon-with-lemon',
            'Рецепт, где есть оба продукта.', [cls.main_category, cls.fish_category],
            [cls.salmon, cls.lemon], prep=20, cook=20, difficulty=Recipe.Difficulty.MEDIUM, rating='4.9',
        )
        cls.salmon_only_recipe = cls.make_recipe(
            'Лосось без лимона', 'salmon-only',
            'Рецепт только с лососем.', [cls.fish_category], [cls.salmon],
            prep=40, cook=40, difficulty=Recipe.Difficulty.HARD, rating='3.5',
        )
        cls.draft_recipe = cls.make_recipe(
            'Скрытый черновик', 'hidden-draft', 'Не должен быть публичным.',
            [cls.main_category], [cls.chicken], prep=10, cook=10,
            difficulty=Recipe.Difficulty.EASY, rating='5.0', status=Recipe.PublicationStatus.DRAFT,
        )
        for index in range(13):
            cls.make_recipe(
                f'Страница {index}', f'page-recipe-{index}', 'Для проверки пагинации.',
                [cls.main_category], [cls.chicken], prep=15, cook=15,
                difficulty=Recipe.Difficulty.EASY, rating='4.0',
            )

    @classmethod
    def product(cls, name):
        return Product.objects.get_or_create(normalized_name=name.lower(), defaults={'name': name})[0]

    @classmethod
    def make_recipe(cls, title, slug, description, categories, products, *, prep, cook, difficulty, rating, status=Recipe.PublicationStatus.PUBLISHED):
        recipe = Recipe.objects.create(
            title=title, slug=slug, description=description, base_servings=2,
            prep_minutes=prep, cook_minutes=cook, difficulty=difficulty, rating=rating,
            publication_status=status, created_by=cls.actor,
        )
        recipe.categories.set(categories)
        for order, product in enumerate(products):
            RecipeIngredient.objects.create(recipe=recipe, product=product, sort_order=order)
        return recipe

    def catalog_url(self):
        return reverse('recipes:recipe_list')

    def recipe_slugs(self, response):
        return {recipe.slug for recipe in response.context['recipes']}

    def test_public_sees_published_but_not_draft_and_no_create_link(self):
        response = self.client.get(self.catalog_url(), {'q': 'Быстрый лимонный'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.fast_recipe.slug, self.recipe_slugs(response))
        self.assertNotIn(self.draft_recipe.slug, self.recipe_slugs(response))
        self.assertNotContains(response, 'Добавить рецепт')

    def test_owner_sees_drafts_and_create_link(self):
        self.client.force_login(self.actor)
        response = self.client.get(self.catalog_url(), {'q': 'Скрытый черновик'})

        self.assertIn(self.draft_recipe.slug, self.recipe_slugs(response))
        self.assertContains(response, 'Черновик')
        self.assertContains(response, 'Добавить рецепт')

    def test_search_matches_title_and_description(self):
        title_response = self.client.get(self.catalog_url(), {'q': 'лимонный завтрак'})
        description_response = self.client.get(self.catalog_url(), {'q': 'ярким лимонным'})

        self.assertEqual(self.recipe_slugs(title_response), {self.fast_recipe.slug})
        self.assertEqual(self.recipe_slugs(description_response), {self.fast_recipe.slug})

    def test_category_filter_uses_or_semantics(self):
        response = self.client.get(
            self.catalog_url(),
            {'category': [self.breakfast_category.slug, self.fish_category.slug]},
        )
        slugs = self.recipe_slugs(response)

        self.assertIn(self.fast_recipe.slug, slugs)
        self.assertIn(self.combo_recipe.slug, slugs)
        self.assertIn(self.salmon_only_recipe.slug, slugs)

    def test_product_filter_uses_and_semantics(self):
        response = self.client.get(self.catalog_url(), {'product': ['лосось', 'лимон']})

        self.assertEqual(self.recipe_slugs(response), {self.combo_recipe.slug, 'orzo-s-lososem'})

    def test_filters_time_difficulty_and_rating(self):
        response = self.client.get(self.catalog_url(), {'q': 'Быстрый лимонный', 'time': '30', 'difficulty': 'easy', 'rating': '4'})

        self.assertIn(self.fast_recipe.slug, self.recipe_slugs(response))
        self.assertNotIn(self.combo_recipe.slug, self.recipe_slugs(response))

    def test_sorting_by_title_rating_and_time(self):
        title_response = self.client.get(self.catalog_url(), {'sort': 'title'})
        rating_response = self.client.get(self.catalog_url(), {'sort': '-rating'})
        time_response = self.client.get(self.catalog_url(), {'sort': 'time'})

        self.assertEqual(title_response.context['recipes'][0].title, 'Быстрый лимонный завтрак')
        self.assertEqual(rating_response.context['recipes'][0].slug, self.combo_recipe.slug)
        self.assertEqual(time_response.context['recipes'][0].slug, self.fast_recipe.slug)

    def test_invalid_params_do_not_fail_and_reset_url_is_clean(self):
        response = self.client.get(
            self.catalog_url(),
            {'time': 'invalid', 'difficulty': 'wrong', 'rating': '99', 'sort': 'unknown'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('recipes:recipe_list'), '/recipes/')
        self.assertContains(response, 'Сбросить фильтры', count=0)

    def test_pagination_and_filter_query_string(self):
        response = self.client.get(self.catalog_url(), {'category': self.main_category.slug, 'q': 'Страница', 'page': '2'})

        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'category=osnovnye-blyuda')
        self.assertContains(response, 'q=%D0%A1%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D0%B0')

    def test_m2m_filters_do_not_duplicate_cards(self):
        response = self.client.get(self.catalog_url(), {'q': 'лосось', 'category': self.fish_category.slug})
        slugs = [recipe.slug for recipe in response.context['recipes']]

        self.assertEqual(len(slugs), len(set(slugs)))

    def test_catalog_uses_bounded_number_of_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.catalog_url())
            list(response.context['recipes'])

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 6)
