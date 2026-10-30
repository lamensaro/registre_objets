from django.urls import path

from . import views


urlpatterns = [
    path("", views.liste_objets, name="liste_objets"),
    path("gestion/objets/ajouter/", views.ajouter_objet, name="ajouter_objet"),
    path("objets/<int:pk>/", views.detail_objet, name="detail_objet"),
    path("mes-reclamations/", views.mes_reclamations, name="mes_reclamations"),
    path(
        "notifications/reclamations/",
        views.notifications_reclamations,
        name="notifications_reclamations",
    ),
    path("reclamations/<int:pk>/", views.detail_reclamation, name="detail_reclamation"),
    path("gestion/reclamations/", views.gestion_reclamations, name="gestion_reclamations"),
    path(
        "gestion/reclamations/<int:pk>/",
        views.detail_gestion_reclamation,
        name="detail_gestion_reclamation",
    ),
]
