from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
    )

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'id']

    def save(self, *args, **kwargs):
        self.normalized_name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=80, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.abbreviation


class Recipe(models.Model):
    class PublicationStatus(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликован'

    class RecipeStatus(models.TextChoices):
        UNVERIFIED = 'unverified', 'Не проверено'
        VERIFIED = 'verified', 'Проверено'
        NEEDS_WORK = 'needs_work', 'В доработке'

    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Легко'
        MEDIUM = 'medium', 'Средне'
        HARD = 'hard', 'Сложно'

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    publication_status = models.CharField(
        max_length=12,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    recipe_status = models.CharField(
        max_length=12,
        choices=RecipeStatus.choices,
        default=RecipeStatus.UNVERIFIED,
    )
    base_servings = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prep_minutes = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    cook_minutes = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('1.0')), MaxValueValidator(Decimal('5.0'))],
    )
    source_url = models.URLField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recipes',
    )
    categories = models.ManyToManyField(Category, related_name='recipes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at', 'id']

    @property
    def total_minutes(self):
        return self.prep_minutes + self.cook_minutes

    def get_absolute_url(self):
        return reverse('recipes:recipe_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title


class IngredientGroup(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredient_groups')
    name = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name or f'Ингредиенты: {self.recipe}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    group = models.ForeignKey(
        IngredientGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ingredients',
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='recipe_ingredients')
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    unit = models.ForeignKey(
        Unit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recipe_ingredients',
    )
    note = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.product} — {self.recipe}'


class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=255)
    text = models.TextField()
    sort_order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='recipes/steps/', blank=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.recipe}: {self.title}'


class RecipeImage(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='recipes/images/')
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'Изображение: {self.recipe}'


class RecipeNote(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='recipe_notes')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.author}: {self.recipe}'
