from io import BytesIO
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import ObjetTrouve, Reclamation


class RegistreObjetsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gestionnaire = user_model.objects.create_user(
            username="gestionnaire",
            password="test-password",
            is_staff=True,
        )
        self.proprietaire = user_model.objects.create_user(
            username="proprietaire",
            password="test-password",
        )
        self.autre_utilisateur = user_model.objects.create_user(
            username="autre",
            password="test-password",
        )
        self.objet = ObjetTrouve.objects.create(
            categorie=ObjetTrouve.Categorie.ELECTRONIQUE,
            description="Téléphone noir",
            lieu_decouverte="Bibliothèque",
            date_decouverte=timezone.localdate(),
            publie_par=self.gestionnaire,
        )

    def test_public_can_search_objects_but_not_see_claim_details(self):
        Reclamation.objects.create(
            objet=self.objet,
            auteur=self.proprietaire,
            description_complementaire="Détail privé secret",
        )
        response = self.client.get(reverse("liste_objets"), {"q": "Téléphone"})
        self.assertContains(response, "Téléphone noir")
        self.assertNotContains(response, "Détail privé secret")

    def test_claim_requires_login_and_owner_only_sees_claim(self):
        response = self.client.post(
            reverse("detail_objet", args=[self.objet.pk]),
            {"description_complementaire": "Je connais le numéro de série."},
        )
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('detail_objet', args=[self.objet.pk])}",
        )
        reclamation = Reclamation.objects.create(
            objet=self.objet,
            auteur=self.proprietaire,
            description_complementaire="Détail privé secret",
        )
        self.client.force_login(self.autre_utilisateur)
        response = self.client.get(reverse("detail_reclamation", args=[reclamation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_claimant_is_notified_when_reclamation_status_changes(self):
        reclamation = Reclamation.objects.create(
            objet=self.objet,
            auteur=self.proprietaire,
            description_complementaire="Je connais le numéro de série.",
        )
        self.client.force_login(self.proprietaire)
        endpoint = reverse("notifications_reclamations")

        initial_response = self.client.get(endpoint)
        self.assertEqual(initial_response.json(), {"notifications": []})

        reclamation.etat = Reclamation.Etat.ACCEPTEE
        reclamation.save(update_fields=["etat"])
        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["notifications"],
            [
                {
                    "objet": self.objet.description,
                    "etat": "Acceptée",
                    "url": reverse("detail_reclamation", args=[reclamation.pk]),
                }
            ],
        )
        self.assertEqual(self.client.get(endpoint).json(), {"notifications": []})

    def test_staff_can_publish_object_with_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="green").save(image_buffer, format="PNG")
        image_upload = SimpleUploadedFile(
            "objet.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        self.client.force_login(self.proprietaire)
        response = self.client.get(reverse("ajouter_objet"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('ajouter_objet')}",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.client.force_login(self.gestionnaire)
                response = self.client.post(
                    reverse("ajouter_objet"),
                    {
                        "categorie": ObjetTrouve.Categorie.ELECTRONIQUE,
                        "description": "Téléphone retrouvé",
                        "lieu_decouverte": "Hall principal",
                        "date_decouverte": timezone.localdate().isoformat(),
                        "image": image_upload,
                    },
                )
                objet = ObjetTrouve.objects.get(description="Téléphone retrouvé")

                self.assertRedirects(
                    response,
                    reverse("detail_objet", args=[objet.pk]),
                )
                self.assertEqual(objet.publie_par, self.gestionnaire)
                self.assertTrue(objet.image)

                detail = self.client.get(reverse("detail_objet", args=[objet.pk]))
                self.assertContains(detail, objet.image.url)

    def test_accepting_one_claim_refuses_other_pending_claims(self):
        premiere = Reclamation.objects.create(
            objet=self.objet,
            auteur=self.proprietaire,
            description_complementaire="Détails du propriétaire.",
        )
        seconde = Reclamation.objects.create(
            objet=self.objet,
            auteur=self.autre_utilisateur,
            description_complementaire="Autres détails.",
        )
        self.client.force_login(self.gestionnaire)
        response = self.client.post(
            reverse("detail_gestion_reclamation", args=[premiere.pk]),
            {"action": "accepter", "note_decision": "Vérification concluante."},
        )
        self.assertRedirects(
            response,
            reverse("detail_gestion_reclamation", args=[premiere.pk]),
        )
        premiere.refresh_from_db()
        seconde.refresh_from_db()
        self.assertEqual(premiere.etat, Reclamation.Etat.ACCEPTEE)
        self.assertEqual(seconde.etat, Reclamation.Etat.REFUSEE)

    def test_delivery_closes_claims_for_object(self):
        reclamation = Reclamation.objects.create(
            objet=self.objet,
            auteur=self.proprietaire,
            description_complementaire="Détails du propriétaire.",
            etat=Reclamation.Etat.ACCEPTEE,
        )
        self.client.force_login(self.gestionnaire)
        self.client.post(
            reverse("detail_gestion_reclamation", args=[reclamation.pk]),
            {"action": "remettre"},
        )
        reclamation.refresh_from_db()
        self.objet.refresh_from_db()
        self.assertEqual(reclamation.etat, Reclamation.Etat.REMISE)
        self.assertIsNotNone(self.objet.remis_le)
        self.client.force_login(self.autre_utilisateur)
        response = self.client.post(
            reverse("detail_objet", args=[self.objet.pk]),
            {"description_complementaire": "Nouvelle réclamation"},
        )
        self.assertRedirects(response, reverse("detail_objet", args=[self.objet.pk]))
        self.assertEqual(self.objet.reclamations.count(), 1)
