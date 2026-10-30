# Registre des objets trouvés — Django

Application de démonstration pour publier les objets trouvés sur un campus et gérer leurs réclamations.

## Démarrage local

Depuis le dossier `registre_objets` :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py makemigrations objets_trouves
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```

Le registre est accessible à `http://127.0.0.1:8000/`. Le compte superutilisateur
peut publier des objets, avec une photo facultative, depuis `/gestion/objets/ajouter/`
ou `/admin/`, et traiter les réclamations dans `/gestion/reclamations/`. Créez les
comptes des utilisateurs via l’administration Django (`/admin/auth/user/add/`) ou
branchez votre mécanisme de création de compte.

Les images téléversées sont stockées dans `media/objets/` en développement. En
production, configurez un stockage de médias dédié et servez les fichiers téléversés
via votre serveur web ou un service de stockage adapté.

## Règles et confidentialité

- La recherche publique porte sur la description générale et le lieu.
- Les détails complémentaires d’une réclamation ne sont visibles que par son auteur
  et un compte `is_staff`.
- Les comptes connectés peuvent déposer une réclamation ; un même utilisateur ne
  peut avoir qu’une réclamation en attente pour un objet.
- L’acceptation d’une réclamation refuse les autres réclamations encore en attente.
- Un objet ne peut avoir qu’une réclamation acceptée ou remise ; l’objet remis ne
  peut plus recevoir de réclamation.
- Seul un gestionnaire peut accepter, refuser ou enregistrer une remise.

Pour un déploiement, configurez `DJANGO_SECRET_KEY`, désactivez `DJANGO_DEBUG` et
remplacez SQLite par une base adaptée à votre infrastructure. Utilisez HTTPS et
un flux de création/réinitialisation de comptes conforme aux règles du campus.
