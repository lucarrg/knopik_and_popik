from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .actors import get_recipe_actor
from .models import Recipe, RecipeNote


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
