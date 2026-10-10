from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from recipes.models import Category, IngredientGroup, Product, Recipe, RecipeImage, RecipeIngredient, RecipeNote, RecipeStep, Unit


class Command(BaseCommand):
    help = 'Create or update the idempotent Орзо с лососем demo recipe.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        author, _ = user_model.objects.get_or_create(username='masha-demo')
        author.first_name = 'Маша'
        author.set_unusable_password()
        author.save(update_fields=['first_name', 'password'])

        recipe, _ = Recipe.objects.update_or_create(
            slug='orzo-s-lososem',
            defaults={
                'title': 'Орзо с лососем',
                'description': 'Нежное орзо со сливочным соусом и лососем.',
                'publication_status': Recipe.PublicationStatus.PUBLISHED,
                'recipe_status': Recipe.RecipeStatus.VERIFIED,
                'base_servings': 4,
                'prep_minutes': 15,
                'cook_minutes': 30,
                'difficulty': Recipe.Difficulty.MEDIUM,
                'rating': Decimal('4.8'),
                'source_url': 'https://example.com/recipe/orzo-salmon',
                'created_by': author,
                'published_at': timezone.now(),
            },
        )

        categories = []
        for name, slug in (('Основные блюда', 'osnovnye-blyuda'), ('Рыба', 'ryba')):
            category, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            if category.name != name:
                category.name = name
                category.save(update_fields=['name'])
            categories.append(category)
        recipe.categories.set(categories)

        units = {}
        for name, abbreviation in (
            ('Грамм', 'г'),
            ('Штука', 'шт.'),
            ('Зубчик', 'зубчика'),
            ('Миллилитр', 'мл'),
            ('Столовая ложка', 'ст. л.'),
        ):
            unit, _ = Unit.objects.get_or_create(abbreviation=abbreviation, defaults={'name': name})
            units[abbreviation] = unit

        group, _ = IngredientGroup.objects.get_or_create(recipe=recipe, name='Основное')
        group.sort_order = 0
        group.save(update_fields=['sort_order'])

        ingredients = (
            ('Лосось', Decimal('400'), 'г', ''),
            ('Орзо', Decimal('250'), 'г', ''),
            ('Шпинат', Decimal('150'), 'г', ''),
            ('Лук репчатый', Decimal('1'), 'шт.', ''),
            ('Чеснок', Decimal('2'), 'зубчика', ''),
            ('Сливки 20%', Decimal('200'), 'мл', ''),
            ('Пармезан', Decimal('50'), 'г', ''),
            ('Лимон', Decimal('1'), 'шт.', ''),
            ('Оливковое масло', Decimal('2'), 'ст. л.', ''),
            ('Соль', None, None, 'по вкусу'),
            ('Чёрный перец', None, None, 'по вкусу'),
        )
        for sort_order, (name, quantity, abbreviation, note) in enumerate(ingredients):
            normalized_name = name.strip().lower()
            product, _ = Product.objects.get_or_create(
                normalized_name=normalized_name,
                defaults={'name': name},
            )
            if product.name != name:
                product.name = name
                product.save(update_fields=['name', 'normalized_name'])
            ingredient, _ = RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                group=group,
                product=product,
            )
            ingredient.quantity = quantity
            ingredient.unit = units.get(abbreviation)
            ingredient.note = note
            ingredient.sort_order = sort_order
            ingredient.save()

        steps = (
            ('Подготовьте продукты', 'Лук нарежьте мелким кубиком, чеснок измельчите. Лосось обсушите и разделите на крупные кусочки, лимон натрите на мелкой тёрке.'),
            ('Обжарьте основу', 'В глубокой сковороде разогрейте оливковое масло. Обжарьте лук до мягкости, добавьте чеснок и орзо, перемешайте, чтобы крупинки покрылись маслом.'),
            ('Добавьте сливочность', 'Влейте горячую воду или бульон небольшими порциями и готовьте орзо до мягкости. Добавьте сливки, пармезан и лимонную цедру, посолите и поперчите.'),
            ('Соберите блюдо', 'Выложите в сковороду лосось и шпинат, аккуратно перемешайте. Накройте на минуту, затем разложите по тарелкам и добавьте немного лимонного сока.'),
        )
        for sort_order, (title, text) in enumerate(steps):
            RecipeStep.objects.update_or_create(
                recipe=recipe,
                sort_order=sort_order,
                defaults={'title': title, 'text': text},
            )

        demo_image_path = settings.BASE_DIR / 'static' / 'images' / 'demo' / 'salmon-orzo.png'
        if demo_image_path.exists():
            cover_image, _ = RecipeImage.objects.get_or_create(
                recipe=recipe,
                is_cover=True,
                defaults={'alt_text': 'Орзо с лососем в сливочном соусе', 'sort_order': 0},
            )
            if not cover_image.image:
                with demo_image_path.open('rb') as image_file:
                    cover_image.image.save('demo/salmon-orzo.png', File(image_file), save=True)

            for step in recipe.steps.filter(sort_order__in=(0, 2)):
                if not step.image:
                    with demo_image_path.open('rb') as image_file:
                        step.image.save('demo/salmon-orzo.png', File(image_file), save=True)

        note_text = 'Я добавляю шпинат в самом конце: он остаётся ярким и не теряет свежесть рядом с тёплым сливочным соусом.'
        RecipeNote.objects.get_or_create(recipe=recipe, author=author, text=note_text)

        self.stdout.write(self.style.SUCCESS(f'Demo recipe ready: {recipe.get_absolute_url()}'))
