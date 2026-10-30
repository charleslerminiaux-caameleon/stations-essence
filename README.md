# Prix Carburants

Carte des stations-essence en France avec les prix des carburants en temps réel
(données : [data.economie.gouv.fr](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/)).

En ligne : https://stations.caameleon.com

## Déploiement automatique

Chaque push sur `main` envoie le site par FTP sur Hostinger
(workflow `.github/workflows/deploy.yml`). On peut aussi le lancer à la main
depuis l'onglet **Actions → Déploiement Hostinger → Run workflow**.

Réglages à faire une fois dans GitHub (**Settings → Secrets and variables → Actions**) :

| Type     | Nom              | Valeur (hPanel → Fichiers → Comptes FTP)            |
|----------|------------------|-----------------------------------------------------|
| Secret   | `FTP_SERVER`     | Hôte FTP, ex. `ftp.caameleon.com` ou l'adresse IP   |
| Secret   | `FTP_USERNAME`   | Identifiant FTP                                     |
| Secret   | `FTP_PASSWORD`   | Mot de passe FTP                                    |
| Variable | `FTP_SERVER_DIR` | Dossier du sous-domaine, terminé par `/` (facultatif si le compte FTP pointe déjà dessus) |

Le plus simple : créer dans hPanel un compte FTP dédié dont le dossier est celui
du sous-domaine `stations` ; `FTP_SERVER_DIR` est alors inutile.
