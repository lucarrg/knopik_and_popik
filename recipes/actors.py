from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


DEMO_USERNAME = 'masha-demo'


def get_recipe_actor(request):
    if request.user.is_authenticated:
        return request.user

    if settings.DEBUG:
        actor = get_user_model().objects.filter(username=DEMO_USERNAME).first()
        if actor is not None:
            return actor

    raise PermissionDenied('Для изменения заметок требуется авторизация.')
