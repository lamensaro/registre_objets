from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ObjetTrouve(models.Model):
    class Categorie(models.TextChoices):
        ELECTRONIQUE = "electronique", "Électronique"
        VETEMENT = "vetement", "Vêtement"
        DOCUMENT = "document", "Document"
        ACCESSOIRE = "accessoire", "Accessoire"
        AUTRE = "autre", "Autre"

    categorie = models.CharField(max_length=20, choices=Categorie.choices)
    description = models.CharField(max_length=300)
    image = models.ImageField(upload_to="objets/", blank=True)
    lieu_decouverte = models.CharField(max_length=160)
    date_decouverte = models.DateField()
    publie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="objets_publies",
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    remis_le = models.DateTimeField(null=True, blank=True)
    remis_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="objets_retrouves",
        null=True,
        blank=True,
    )
    remis_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="objets_remis",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-date_decouverte", "-cree_le"]
        verbose_name = "objet trouvé"
        verbose_name_plural = "objets trouvés"

    def __str__(self):
        return f"{self.get_categorie_display()} — {self.lieu_decouverte} ({self.date_decouverte})"

    @property
    def est_remis(self):
        return self.remis_le is not None


class Reclamation(models.Model):
    class Etat(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ACCEPTEE = "acceptee", "Acceptée"
        REFUSEE = "refusee", "Refusée"
        REMISE = "remise", "Remise"

    objet = models.ForeignKey(
        ObjetTrouve,
        on_delete=models.PROTECT,
        related_name="reclamations",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reclamations_objets",
    )
    description_complementaire = models.TextField(
        help_text="Détails privés permettant au gestionnaire de vérifier votre réclamation."
    )
    etat = models.CharField(
        max_length=12,
        choices=Etat.choices,
        default=Etat.EN_ATTENTE,
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    traitee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reclamations_traitees",
        null=True,
        blank=True,
    )
    traitee_le = models.DateTimeField(null=True, blank=True)
    note_decision = models.TextField(blank=True)
    remise_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "réclamation"
        verbose_name_plural = "réclamations"
        constraints = [
            models.UniqueConstraint(
                fields=["objet", "auteur"],
                condition=Q(etat="en_attente"),
                name="une_reclamation_en_attente_par_auteur_objet",
            ),
            models.UniqueConstraint(
                fields=["objet"],
                condition=Q(etat__in=["acceptee", "remise"]),
                name="une_reclamation_gagnante_par_objet",
            ),
        ]

    def __str__(self):
        return f"Réclamation #{self.pk} — {self.objet}"

    def clean(self):
        super().clean()
        if self.etat == self.Etat.REMISE and self.remise_le is None:
            raise ValidationError({"remise_le": "La date de remise est obligatoire."})
        if self.etat != self.Etat.REMISE and self.remise_le is not None:
            raise ValidationError({"remise_le": "Seule une réclamation remise a une date de remise."})

    def save(self, *args, **kwargs):
        if self.etat == self.Etat.REMISE and self.remise_le is None:
            self.remise_le = timezone.now()
        super().save(*args, **kwargs)
