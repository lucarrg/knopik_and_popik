from django.contrib import admin

from .models import (
    Category,
    IngredientGroup,
    Product,
    Recipe,
    RecipeImage,
    RecipeIngredient,
    RecipeNote,
    RecipeStep,
    Unit,
)


class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 0


class IngredientGroupInline(admin.TabularInline):
    model = IngredientGroup
    extra = 0


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 0


class RecipeNoteInline(admin.TabularInline):
    model = RecipeNote
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_status', 'recipe_status', 'difficulty', 'created_at')
    search_fields = ('title',)
    list_filter = ('publication_status', 'recipe_status', 'difficulty', 'categories')
    prepopulated_fields = {'slug': ('title',)}
    inlines = (RecipeImageInline, IngredientGroupInline, RecipeStepInline, RecipeNoteInline)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'normalized_name', 'is_active')
    search_fields = ('name', 'normalized_name')
    list_filter = ('is_active',)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'is_active')
    list_filter = ('is_active',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('product', 'recipe', 'group', 'quantity', 'unit', 'sort_order')
    list_select_related = ('recipe', 'group', 'product', 'unit')


admin.site.register((IngredientGroup, RecipeImage, RecipeNote, RecipeStep))
