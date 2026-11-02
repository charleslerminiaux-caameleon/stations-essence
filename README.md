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


Le dossier de destination est fixé dans le workflow : `stations/`. Le compte FTP
démarre dans `public_html` de caameleon.com, et le sous-domaine
`stations.caameleon.com` pointe vers `public_html/stations`. La variable
`FTP_SERVER_DIR` n'est plus utilisée.
