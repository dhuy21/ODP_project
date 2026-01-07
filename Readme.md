# ODP - Orchestration & Deployment Platform

## Membres

- Mehdi Ouseggua
- Vinh Tri NGUYEN
- Dinh Huy NGUYEN
- Khalid
- Thanh Tu VO
- Gia Khanh NGUYEN

## Projet

**Automatique "Pentest"**

## Enoncé

Plateforme de provisioning et d’orchestration d’un pool de ressources conteneurisées (workers) qui permet de réserver et délivrer des ressources à des clients, de surveiller leur état, et de remplacer automatiquement les ressources manquantes afin de maintenir un niveau de service défini.

## Architecture Nouvelle (v2)

Ce projet a été migré vers une architecture MVC robuste :

- **Backend :** Python (Flask) + Docker SDK (remplace les scripts Bash)
- **Base de données :** MySQL (remplace les fichiers JSON)
- **Frontend :** HTML/JS/CSS (Jinja2)

## Installation et Lancement

### 1. Prérequis

- Python 3.8+
- Docker & Docker Compose
- MySQL Server

### 2. Installation

Installer les dépendances Python :

```bash
pip install -r requirements.txt
```

### 3. Configuration de la Base de Données

Assurez-vous que MySQL est lancé et créez la base de données :

```bash
# Importer le schéma (Users + Pool Nodes)
mysql -u root -p < database/db_schema.sql
```

### 4. Initialisation du Pool

Lancer le script Python pour créer le réseau Docker et les 30 conteneurs (workers) :

```bash
# Cette étape remplace l'ancien "./pool_manager.sh init"
python3 init_pool.py
```

### 5. Démarrer l'Application Web

```bash
cd web
python3 app.py
```

Accédez à l'application via : http://localhost:5001

---

## Commandes Utiles

- **Vérifier l'état du pool (DB) :**
  Se connecter à MySQL et exécuter :

  ```sql
  SELECT * FROM pool_nodes;
  ```

- **Nettoyage (Optionnel) :**
  Pour supprimer tous les conteneurs :
  ```bash
  python3 kill_pool.py  # si disponible
  # ou via Docker
  docker rm -f $(docker ps -aq --filter name=pool-node)
  ```

```

```
