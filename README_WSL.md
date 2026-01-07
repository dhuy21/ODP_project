# Guide d'installation WSL (Windows)

Ce document décrit les étapes nécessaires pour configurer et exécuter ce projet sur Windows en utilisant WSL2 (Windows Subsystem for Linux). Le projet est une plateforme de provisioning et d’orchestration d’un pool de ressources conteneurisées (workers).

## 1. Prérequis (sur Windows)

Avant de commencer, installez et configurez les éléments suivants :

- `WSL2` : exécutez `wsl --install` dans PowerShell (admin).
- Une distribution Linux (Ubuntu 22.04 LTS ou 24.04 LTS) depuis le Microsoft Store.
- Docker Desktop pour Windows.
- Intégration WSL dans Docker Desktop : `Settings > Resources > WSL integration`, activez votre distribution Ubuntu.

## 2. Configuration de l'environnement WSL (terminal Ubuntu)

Ouvrez votre terminal Ubuntu (ex. _Ubuntu 22.04 LTS_) et suivez ces étapes :

### Étape 1 : Mettre à jour et installer les dépendances système

Packages requis : `ansible`, `python3-pip`, `python3-venv`, `dos2unix`, `python3-passlib`.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ansible python3-pip python3-venv dos2unix python3-passlib
```

### Étape 2 : Préparer les fichiers du projet

Placez les fichiers dans `~/ODP_project`, puis :

```bash
cd ~/ODP_project
dos2unix allocates.sh
dos2unix Docker/ssh/entrypoint.sh
dos2unix pool_manager.sh
chmod +x allocates.sh
chmod +x Docker/ssh/entrypoint.sh
chmod +x pool_manager.sh
```

### Étape 3 : Configurer la clé SSH

Le projet utilise une clé SSH Vagrant non sécurisée pour accéder aux conteneurs.

```bash
mkdir -p ~/.vagrant.d
curl -L https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant -o ~/.vagrant.d/insecure_private_key
chmod 600 ~/.vagrant.d/insecure_private_key
```

### Étape 4 : Installer et configurer MySQL

1. **Installer MySQL Server dans WSL :**

```bash
sudo apt update
sudo apt install -y mysql-server
```

2. **Démarrer le service MySQL :**

```bash
sudo service mysql start
```

3. **Configurer l’utilisateur root (optionnel, pour mot de passe simple) :**

```bash
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';
FLUSH PRIVILEGES;
exit
```

4. **Importer le schéma de base de données :**

```bash
mysql -u root -p < database/db_schema.sql
# (mot de passe par défaut : root)
```

5. **Migrer les anciens utilisateurs (JSON) vers MySQL :**

```bash
cd database
python3 migrate_data.py
cd ..
```

### Étape 5 : Créer l'environnement virtuel Python

Utiliser un environnement virtuel évite l’erreur `externally-managed-environment`.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> L'invite de commande doit maintenant commencer par `(venv)`.

## 3. Lancement du projet

Avant de lancer l’application, assurez-vous que :

- Le service MySQL est démarré (`sudo service mysql start`)
- L’environnement virtuel Python est activé (`source venv/bin/activate`)

Lancez Flask :

```bash
python3 web/app.py
```

## 4. Utilisation

- Ouvrez un navigateur web sur Windows.
- Rendez-vous sur `http://localhost:5001` ou `http://127.0.0.1:5001`.
- Remplissez le formulaire pour créer l’infrastructure.
- Patientez jusqu’à la fin du provisionnement.
- Vous serez redirigé vers un tableau de bord pour accéder au terminal web de vos conteneurs.

## 5. Annexe : Résolution des erreurs d'environnement

### Erreur 0x80370114 (Échec de l'installation de WSL)

- **Cause** : Virtualisation matérielle (Intel VT-x / AMD-V) désactivée ou fonctionnalités Windows manquantes.
- **Solutions** :
  - Activer VT-x / AMD-V dans le BIOS/UEFI.
  - Dans "Activer ou désactiver des fonctionnalités Windows", cocher _Plateforme de machine virtuelle_ et _Sous-système Windows pour Linux_.
  - Redémarrer puis relancer `wsl --install`.

### Erreur `docker: not found` (terminal Ubuntu)

- **Cause** : Docker Desktop n’est pas lancé ou l’intégration WSL est désactivée.
- **Solutions** :
  - Lancer Docker Desktop sur Windows.
  - Vérifier `Settings > Resources > WSL integration` et activer la distribution (ex. `Ubuntu-24.04`).
  - Redémarrer le terminal Ubuntu.
