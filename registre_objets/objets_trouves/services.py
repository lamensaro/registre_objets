from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ObjetTrouve, Reclamation


@transaction.atomic
def deposer_reclamation(*, objet_id, auteur, description_complementaire):
    objet = ObjetTrouve.objects.select_for_update().get(pk=objet_id)
    if objet.est_remis:
        raise ValidationError("Cet objet a déjà été remis. Il n'est plus possible de le réclamer.")
    if objet.reclamations.filter(etat__in=[Reclamation.Etat.ACCEPTEE, Reclamation.Etat.REMISE]).exists():
        raise ValidationError("Une réclamation a déjà été acceptée pour cet objet.")
    if objet.reclamations.filter(auteur=auteur, etat=Reclamation.Etat.EN_ATTENTE).exists():
        raise ValidationError("Vous avez déjà une réclamation en attente pour cet objet.")
    return Reclamation.objects.create(
        objet=objet,
        auteur=auteur,
        description_complementaire=description_complementaire,
    )


@transaction.atomic
def traiter_reclamation(*, reclamation_id, gestionnaire, action, note_decision=""):
    reclamation = (
        Reclamation.objects.select_for_update()
        .select_related("objet")
        .get(pk=reclamation_id)
    )
    objet = ObjetTrouve.objects.select_for_update().get(pk=reclamation.objet_id)

    if reclamation.etat != Reclamation.Etat.EN_ATTENTE:
        raise ValidationError("Cette réclamation a déjà été traitée.")

    if action == "refuser":
        reclamation.etat = Reclamation.Etat.REFUSEE
        reclamation.traitee_par = gestionnaire
        reclamation.traitee_le = timezone.now()
        reclamation.note_decision = note_decision
        reclamation.save(
            update_fields=["etat", "traitee_par", "traitee_le", "note_decision"]
        )
        return reclamation

    if action != "accepter":
        raise ValidationError("Action de traitement inconnue.")
    if objet.est_remis:
        raise ValidationError("Cet objet a déjà été remis.")
    if objet.reclamations.filter(
        etat__in=[Reclamation.Etat.ACCEPTEE, Reclamation.Etat.REMISE]
    ).exclude(pk=reclamation.pk).exists():
        raise ValidationError("Une autre réclamation a déjà été acceptée pour cet objet.")

    now = timezone.now()
    reclamation.etat = Reclamation.Etat.ACCEPTEE
    reclamation.traitee_par = gestionnaire
    reclamation.traitee_le = now
    reclamation.note_decision = note_decision
    reclamation.save(
        update_fields=["etat", "traitee_par", "traitee_le", "note_decision"]
    )

    objet.reclamations.filter(etat=Reclamation.Etat.EN_ATTENTE).exclude(
        pk=reclamation.pk
    ).update(
        etat=Reclamation.Etat.REFUSEE,
        traitee_par=gestionnaire,
        traitee_le=now,
        note_decision="Une autre réclamation a été acceptée.",
    )
    return reclamation


@transaction.atomic
def enregistrer_remise(*, reclamation_id, gestionnaire):
    reclamation = (
        Reclamation.objects.select_for_update()
        .select_related("objet")
        .get(pk=reclamation_id)
    )
    objet = ObjetTrouve.objects.select_for_update().get(pk=reclamation.objet_id)
    if reclamation.etat != Reclamation.Etat.ACCEPTEE:
        raise ValidationError("Seule une réclamation acceptée peut être remise.")
    if objet.est_remis:
        raise ValidationError("La remise de cet objet a déjà été enregistrée.")

    now = timezone.now()
    reclamation.etat = Reclamation.Etat.REMISE
    reclamation.remise_le = now
    reclamation.save(update_fields=["etat", "remise_le"])
    objet.remis_le = now
    objet.remis_a = reclamation.auteur
    objet.remis_par = gestionnaire
    objet.save(update_fields=["remis_le", "remis_a", "remis_par"])
    return reclamation
