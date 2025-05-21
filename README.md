# BA Copilot

BA Copilot est un outil d'aide à l'analyse fonctionnelle pour les Business Analysts. Il permet de générer et gérer des spécifications fonctionnelles, des diagrammes et des éléments structurés (Epics, Features, User Stories, etc.) à l'aide de l'IA.

## Fonctionnalités

- **Génération de spécifications** via des agents IA
- **Création de diagrammes fonctionnels** (mindmap Mermaid)
- **Gestion de projets** avec une structure hiérarchique
- **Organisation des éléments fonctionnels** (Epics, Features, User Stories, Use Cases, Requirements)
- **Visualisation interactive** avec édition des nœuds
- **Vue par liste** pour chaque type d'élément

## Architecture

L'application est composée de :

- **Backend** : API FastAPI en Python avec une base de données SQLite
- **Frontend** : Application React/TypeScript avec Vite

## Prérequis

- Python 3.8+ 
- Node.js 18+
- npm ou yarn

## Installation

### Backend

1. Cloner le dépôt
   ```bash
   git clone https://github.com/votre-repo/ba-copilot.git
   cd ba-copilot
   ```

2. Installer les dépendances Python avec Poetry
   ```bash
   poetry install
   ```

3. Ou utiliser pip
   ```bash
   pip install -r requirements.txt
   ```

4. Initialiser la base de données (au premier lancement)
   ```bash
   cd src
   python -c "from models import init_db; init_db()"
   ```

5. Si vous migrez depuis une ancienne version avec stockage en mémoire
   ```bash
   # Sauvegarder les données en mémoire
   python save_memory_data.py
   
   # Migrer les données vers la BD
   python migrate_data.py memory_data.json
   ```

### Frontend

1. Se déplacer dans le répertoire du frontend
   ```bash
   cd ba-copilot-ui
   ```

2. Installer les dépendances
   ```bash
   npm install
   # ou
   yarn install
   ```

3. (Optionnel) Configurer l'URL de l'API 
   
   Vous pouvez modifier l'URL de l'API dans le fichier `src/ProjectDetailPage.tsx` en remplaçant :
   ```typescript
   const API_URL = 'http://192.168.1.93:8000';
   ```
   par l'URL de votre serveur API.

## Démarrage

1. Lancer le backend
   ```bash
   cd src
   python api_new.py
   ```
   Le serveur démarre sur http://localhost:8000

2. Lancer le frontend (dans un autre terminal)
   ```bash
   cd ba-copilot-ui
   npm run dev
   # ou
   yarn dev
   ```
   L'application est accessible sur http://localhost:5173

## Utilisation

### Générer des spécifications

1. Créez un nouveau projet ou sélectionnez un projet existant
2. Dans l'onglet "Générer des spécifications", saisissez une description du besoin
3. Cliquez sur "Générer via agents IA" pour obtenir une analyse détaillée

### Créer un diagramme fonctionnel

1. Dans l'onglet "Diagramme fonctionnel", décrivez l'objectif du diagramme
2. Cliquez sur "Générer le diagramme Mermaid"
3. Le diagramme mindmap s'affiche avec les éléments fonctionnels (Epics, Features, etc.)
4. Cliquez sur un nœud du diagramme pour afficher/modifier ses détails

### Gestion des éléments par type

1. Dans l'onglet "Liste par type", sélectionnez un type d'élément (Epic, Feature, etc.)
2. Consultez la liste de tous les éléments de ce type dans votre projet
3. Cliquez sur "Éditer" pour modifier un élément

## Modèle de données

L'application utilise une structure hiérarchique :

- **Projet**
  - **Epic** (Grand ensemble fonctionnel)
    - **Feature** (Fonctionnalité spécifique)
      - **User Story** (Besoin utilisateur concret)
        - **Use Case** (Scénario d'utilisation)
          - **Requirement** (Exigence technique/fonctionnelle)

## API REST

Le backend expose une API REST complète pour gérer toutes les ressources :

### Projets
- `GET /projects` - Liste tous les projets
- `POST /projects` - Crée un nouveau projet
- `GET /projects/{project_id}` - Récupère les détails d'un projet
- `PUT /projects/{project_id}` - Met à jour un projet
- `DELETE /projects/{project_id}` - Supprime un projet

### Structure de projet
- `GET /projects/{project_id}/structure` - Récupère toute la structure d'un projet

### Éléments
- `GET /projects/{project_id}/elements` - Liste tous les éléments d'un projet (filtrable par type)
- `POST /projects/{project_id}/elements` - Crée un nouvel élément
- `GET /elements/{element_id}` - Récupère un élément spécifique
- `PUT /elements/{element_id}` - Met à jour un élément
- `DELETE /elements/{element_id}` - Supprime un élément

### Diagrammes
- `GET /projects/{project_id}/diagrams` - Liste les diagrammes d'un projet
- `POST /projects/{project_id}/diagrams` - Crée un nouveau diagramme

### Génération IA
- `POST /agents/generate_mermaid` - Génère un diagramme Mermaid basé sur un objectif

## Contribuer

Pour contribuer à ce projet, veuillez suivre les étapes suivantes :

1. Forker le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Valider vos modifications (`git commit -m 'Ajout de la fonctionnalité XYZ'`)
4. Pousser vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrir une Pull Request

## License

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.