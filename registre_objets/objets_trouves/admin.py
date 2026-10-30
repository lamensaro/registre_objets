from django.contrib import admin

from .models import ObjetTrouve, Reclamation


@admin.register(ObjetTrouve)
class ObjetTrouveAdmin(admin.ModelAdmin):
    list_display = ("categorie", "lieu_decouverte", "date_decouverte", "remis_le")
    list_filter = ("categorie", "date_decouverte", "remis_le")
    search_fields = ("description", "lieu_decouverte")
    readonly_fields = ("cree_le", "remis_le", "remis_a", "remis_par")


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ("id", "objet", "auteur", "etat", "cree_le")
    list_filter = ("etat", "cree_le")
    search_fields = ("objet__description", "auteur__username")
    readonly_fields = (
        "objet",
        "auteur",
        "description_complementaire",
        "etat",
        "cree_le",
        "traitee_par",
        "traitee_le",
        "note_decision",
        "remise_le",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
