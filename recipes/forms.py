from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import IngredientGroup, Product, Recipe, RecipeImage, RecipeIngredient, RecipeNote, RecipeStep


class RecipeNoteForm(forms.Form):
    text = forms.CharField()

    def clean_text(self):
        text = self.cleaned_data['text'].strip()
        if not text:
            raise forms.ValidationError('Введите текст заметки.')
        return text


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            'title',
            'description',
            'publication_status',
            'recipe_status',
            'base_servings',
            'prep_minutes',
            'cook_minutes',
            'difficulty',
            'rating',
            'source_url',
            'categories',
        ]
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'publication_status': 'Публикация',
            'recipe_status': 'Статус рецепта',
            'base_servings': 'Порции',
            'prep_minutes': 'Подготовка, мин',
            'cook_minutes': 'Готовка, мин',
            'difficulty': 'Сложность',
            'rating': 'Рейтинг',
            'source_url': 'Источник',
            'categories': 'Категории',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'categories': forms.CheckboxSelectMultiple,
        }


class IngredientGroupForm(forms.ModelForm):
    class Meta:
        model = IngredientGroup
        fields = ['name', 'sort_order']
        labels = {'name': 'Название', 'sort_order': 'Порядок'}


class RecipeIngredientForm(forms.ModelForm):
    product_name = forms.CharField(label='Продукт')

    class Meta:
        model = RecipeIngredient
        fields = ['group', 'quantity', 'unit', 'note', 'sort_order']
        labels = {
            'group': 'Группа', 'quantity': 'Количество', 'unit': 'Единица',
            'note': 'Примечание', 'sort_order': 'Порядок',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].required = False
        self.fields['group'].queryset = IngredientGroup.objects.none()
        if self.instance.pk:
            self.fields['product_name'].initial = self.instance.product.name

    def clean_product_name(self):
        return self.cleaned_data['product_name'].strip()

    def save(self, commit=True):
        ingredient = super().save(commit=False)
        product_name = self.cleaned_data['product_name']
        normalized_name = product_name.strip().lower()
        product, _ = Product.objects.get_or_create(
            normalized_name=normalized_name,
            defaults={'name': product_name},
        )
        ingredient.product = product
        if commit:
            ingredient.save()
            self.save_m2m()
        return ingredient


class RecipeStepForm(forms.ModelForm):
    class Meta:
        model = RecipeStep
        fields = ['title', 'text', 'sort_order', 'image']
        labels = {'title': 'Заголовок', 'text': 'Текст', 'sort_order': 'Порядок', 'image': 'Фото шага'}
        widgets = {'text': forms.Textarea(attrs={'rows': 4})}


class RecipeImageForm(forms.ModelForm):
    class Meta:
        model = RecipeImage
        fields = ['image', 'alt_text', 'sort_order', 'is_cover']
        labels = {'image': 'Файл', 'alt_text': 'Описание', 'sort_order': 'Порядок', 'is_cover': 'Обложка'}


class BaseRecipeImageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        cover_count = sum(
            1
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get('DELETE', False)
            and form.cleaned_data.get('is_cover', False)
        )
        if cover_count > 1:
            raise forms.ValidationError('У рецепта может быть только одна обложка.')


IngredientGroupFormSet = inlineformset_factory(
    Recipe,
    IngredientGroup,
    form=IngredientGroupForm,
    extra=1,
    can_delete=True,
)
RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    form=RecipeIngredientForm,
    extra=1,
    can_delete=True,
)
RecipeStepFormSet = inlineformset_factory(
    Recipe,
    RecipeStep,
    form=RecipeStepForm,
    extra=1,
    can_delete=True,
)
RecipeImageFormSet = inlineformset_factory(
    Recipe,
    RecipeImage,
    form=RecipeImageForm,
    formset=BaseRecipeImageFormSet,
    extra=1,
    can_delete=True,
)