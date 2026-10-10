from django.shortcuts import render


def home(request):
    return render(request, 'index.html')


def recipe_list(request):
    return render(request, 'recipes.html')


def recipe_detail(request):
    return render(request, 'recipe.html')
