from django.core.management import call_command
from django.test import TestCase

from .models import Recipe


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
