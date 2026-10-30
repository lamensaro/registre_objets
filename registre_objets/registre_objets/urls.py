from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/connexion/", auth_views.LoginView.as_view(), name="login"),
    path("comptes/deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("objets_trouves.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
