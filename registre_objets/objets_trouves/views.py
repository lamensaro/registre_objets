from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .forms import NoteDecisionForm, ObjetTrouveForm, ReclamationForm
from .models import ObjetTrouve, Reclamation
from .services import deposer_reclamation, enregistrer_remise, traiter_reclamation


def est_gestionnaire(user):
    return user.is_staff


def liste_objets(request):
    objets = ObjetTrouve.objects.all()
    mot_cle = request.GET.get("q", "").strip()
    categorie = request.GET.get("categorie", "").strip()
    if mot_cle:
        objets = objets.filter(description__icontains=mot_cle) | objets.filter(
            lieu_decouverte__icontains=mot_cle
        )
    if categorie in ObjetTrouve.Categorie.values:
        objets = objets.filter(categorie=categorie)
    return render(
        request,
        "objets_trouves/liste_objets.html",
        {
            "objets": objets.distinct(),
            "mot_cle": mot_cle,
            "categorie_selectionnee": categorie,
            "categories": ObjetTrouve.Categorie.choices,
        },
    )


@user_passes_test(est_gestionnaire)
def ajouter_objet(request):
    form = ObjetTrouveForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        objet = form.save(commit=False)
        objet.publie_par = request.user
        objet.save()
        messages.success(request, "L’objet a été publié dans le registre.")
        return redirect("detail_objet", pk=objet.pk)
    return render(request, "objets_trouves/ajouter_objet.html", {"form": form})


def detail_objet(request, pk):
    objet = get_object_or_404(ObjetTrouve, pk=pk)
    peut_reclamer = not objet.est_remis and not objet.reclamations.filter(
        etat__in=[Reclamation.Etat.ACCEPTEE, Reclamation.Etat.REMISE]
    ).exists()
    deja_en_attente = (
        request.user.is_authenticated
        and objet.reclamations.filter(
            auteur=request.user,
            etat=Reclamation.Etat.EN_ATTENTE,
        ).exists()
    )
    form = ReclamationForm()
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        form = ReclamationForm(request.POST)
        if form.is_valid():
            try:
                reclamation = deposer_reclamation(
                    objet_id=objet.pk,
                    auteur=request.user,
                    description_complementaire=form.cleaned_data["description_complementaire"],
                )
            except (ValidationError, IntegrityError) as error:
                message = error.messages[0] if isinstance(error, ValidationError) else (
                    "Une réclamation en attente existe déjà pour cet objet."
                )
                messages.error(request, message)
                return redirect("detail_objet", pk=objet.pk)
            messages.success(request, "Votre réclamation a été enregistrée.")
            return redirect("detail_reclamation", pk=reclamation.pk)
    return render(
        request,
        "objets_trouves/detail_objet.html",
        {
            "objet": objet,
            "form": form,
            "peut_reclamer": peut_reclamer,
            "deja_en_attente": deja_en_attente,
        },
    )


@login_required
def mes_reclamations(request):
    reclamations = Reclamation.objects.filter(auteur=request.user).select_related("objet")
    return render(
        request,
        "objets_trouves/mes_reclamations.html",
        {"reclamations": reclamations},
    )


@login_required
@require_GET
def notifications_reclamations(request):
    reclamations = Reclamation.objects.filter(auteur=request.user).select_related("objet")
    snapshot_key = f"reclamation_status_snapshot:{request.user.pk}"
    ancien_etat = request.session.get(snapshot_key)
    nouvel_etat = {str(reclamation.pk): reclamation.etat for reclamation in reclamations}
    notifications = []

    if ancien_etat is not None:
        libelles = dict(Reclamation.Etat.choices)
        for reclamation in reclamations:
            etat_precedent = ancien_etat.get(str(reclamation.pk))
            if etat_precedent and etat_precedent != reclamation.etat:
                notifications.append(
                    {
                        "objet": reclamation.objet.description,
                        "etat": libelles[reclamation.etat],
                        "url": reverse("detail_reclamation", args=[reclamation.pk]),
                    }
                )

    request.session[snapshot_key] = nouvel_etat
    return JsonResponse({"notifications": notifications})


@login_required
def detail_reclamation(request, pk):
    reclamation = get_object_or_404(
        Reclamation.objects.select_related("objet", "auteur", "traitee_par"),
        pk=pk,
    )
    if not request.user.is_staff and reclamation.auteur_id != request.user.pk:
        from django.http import Http404

        raise Http404
    return render(
        request,
        "objets_trouves/detail_reclamation.html",
        {"reclamation": reclamation},
    )


@user_passes_test(est_gestionnaire)
def gestion_reclamations(request):
    reclamations = Reclamation.objects.select_related("objet", "auteur").order_by(
        "etat", "-cree_le"
    )
    return render(
        request,
        "objets_trouves/gestion_reclamations.html",
        {"reclamations": reclamations},
    )


@user_passes_test(est_gestionnaire)
def detail_gestion_reclamation(request, pk):
    reclamation = get_object_or_404(
        Reclamation.objects.select_related("objet", "auteur", "traitee_par"),
        pk=pk,
    )
    form = NoteDecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action")
        try:
            if action == "remettre":
                enregistrer_remise(
                    reclamation_id=reclamation.pk,
                    gestionnaire=request.user,
                )
            else:
                traiter_reclamation(
                    reclamation_id=reclamation.pk,
                    gestionnaire=request.user,
                    action=action,
                    note_decision=form.cleaned_data["note_decision"],
                )
        except (ValidationError, IntegrityError) as error:
            message = error.messages[0] if isinstance(error, ValidationError) else (
                "Cette réclamation a été modifiée simultanément. Rechargez la page."
            )
            messages.error(request, message)
        else:
            messages.success(request, "La réclamation a été mise à jour.")
            return redirect("detail_gestion_reclamation", pk=reclamation.pk)
    reclamation.refresh_from_db()
    return render(
        request,
        "objets_trouves/detail_gestion_reclamation.html",
        {"reclamation": reclamation, "form": form},
    )
