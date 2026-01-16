# ProAct GMAO - Backend

## Vue d'Ensemble

Le backend de **ProAct** est une API REST robuste et performante développée avec **FastAPI**. Il sert de noyau central pour la gestion des données de maintenance et l'orchestration des modules d'intelligence artificielle.

Conçu selon les principes de l'architecture en couches, il garantit une séparation claire entre les routeurs, la logique métier (services) et l'accès aux données (ORM).

## Stack Technologique

### Core & API
*   **Framework** : [FastAPI](https://fastapi.tiangolo.com/) (Asynchrone, Typage strict)
*   **Serveur** : Uvicorn (ASGI)
*   **Validation** : Pydantic v2

### Données & Persistance
*   **Base de Données** : PostgreSQL 16
*   **ORM** : SQLAlchemy (Async)
*   **Migrations** : Alembic
*   **Vector Store** : FAISS (Recherche de similarité locale)
*   **Cache** : Redis (Optionnel, pour les sessions RAG)

### Intelligence Artificielle & Data Science
*   **LLM Interface** : LangChain / Ollama / Groq API
*   **Analyse de Données** : Pandas, NumPy
*   **Machine Learning** : Scikit-learn (Random Forest, XGBoost pour prédictions)
*   **Computer Vision** : Pillow, PDFPlumber (Traitement OCR)

## Architecture du Projet

Le code source est situé dans le dossier `app/` :

```mermaid
graph TD
    API[FastAPI App] --> Routers[app/routers]
    Routers --> Services[app/services]
    Services --> Models[app/models.py]
    Services --> Schemas[app/schemas.py]
    
    subgraph Services_Layer [Couche Services]
        General[Business Logic]
        RAG[RAG Service]
        ML[ML Models]
        OCR[OCR Service]
    end
    
    Services --> DB[(PostgreSQL)]
    RAG --> VectorDB[(FAISS Index)]
    RAG --> LLM[LLM Provider]
```

### Organisation des Dossiers

*   `app/routers/` : Endpoints API (Interventions, Équipements, Auth, AI).
*   `app/services/` : Logique métier complexe et orchestration IA.
*   `app/models.py` : Définitions des tables SQLAlchemy.
*   `app/schemas.py` : Modèles Pydantic (DTOs).
*   `app/ml_models/` : Modèles de Machine Learning sérialisés (.pkl).
*   `alembic/` : Scripts de migration de base de données.

## Installation et Configuration

### Prérequis

*   Python 3.11+
*   PostgreSQL (ou utiliser SQLite pour dev)
*   Ollama (pour l'IA locale)

### Configuration de l'environnement virtuel

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Variables d'Environnement

Copiez le fichier `.env.example` vers `.env` et configurez les clés :

```ini
# Base de données
DATABASE_URL=postgresql://user:pass@localhost:5432/gmao

# Sécurité (JWT)
SECRET_KEY=votre_cle_secrete_super_securisee
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Intelligence Artificielle
LLM_PROVIDER=ollama # ou 'groq'
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=votre_cle_groq
```

## Démarrage du Serveur

```bash
uvicorn app.main:app --reload
```

L'API sera accessible sur [http://localhost:8000](http://localhost:8000).
La documentation interactive (Swagger UI) est disponible sur [http://localhost:8000/docs](http://localhost:8000/docs).

## Modules IA Détaillés

### 1. RAG (Retrieval-Augmented Generation)
Permet d'interroger la documentation technique.
*   **Ingestion** : Les PDF sont uploadés, parsés, et convertis en embeddings.
*   **Query** : La question utilisateur est vectorisée et comparée à l'index FAISS pour récupérer le contexte pertinent.

### 2. Maintenance Copilot
Assistant intelligent capable de :
*   Analyser les pannes historiques.
*   Suggérer des diagnostics basés sur les symptômes.
*   Générer des résumés d'interventions.

### 3. Moteur de Prédiction (Forecast)
Utilise des algorithmes de régression (Random Forest) pour prédire :
*   **RUL** (Remaining Useful Life) : Durée de vie restante estimée.
*   **MTBF** : Temps moyen avant la prochaine panne.

## Tests

Pour lancer les tests unitaires et d'intégration :

```bash
pytest
```

## Maintenance de la Base de Données

Générer une migration après modification des modèles :
```bash
alembic revision --autogenerate -m "description_changement"
```

Appliquer les migrations :
```bash
alembic upgrade head
```

## Auteurs

*   **Mohamed Amine Darraj**
*   **Adam Khald**
