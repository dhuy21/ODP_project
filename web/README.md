# Dossier `web`

Ce dossier contient l’application web du projet ODP.

## Structure du dossier

```
web/
├── app.py                # Script principal de l’application Flask
├── requirement.txt       # Liste des dépendances Python
├── templates/            # Dossier des templates HTML (Jinja2)
```

## Initialisation de l’application

1. **Installer Python** (version recommandée : 3.8+)

1.5 **Créez un environnement virtuel pour isoler les dépendances**(Optionnel)

```bash
python -v venv venv
source myenv/bin/activate  # For Unix/Linux
.\myenv\Scripts\activate  # For Windows
```

2. **Installer les dépendances** :

Ouvrez un terminal dans le dossier `web` et lancez :
```bash
pip install -r requirement.txt
```

3. **Lancer l’application** :

```bash
python app.py
```

L’application sera accessible sur `http://localhost:5000` (par défaut).

## Notes
- Les templates HTML doivent être placés dans le dossier `templates/`.
- Les styles css sont dans le dossier `static\css`
- Modifiez `requirement.txt` pour ajouter ou mettre à jour les dépendances nécessaires.
