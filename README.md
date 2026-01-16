# ProAct GMAO

**Système de Gestion de Maintenance Assistée par Ordinateur (GMAO) Augmenté par l'IA**

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://www.postgresql.org/)
[![Ollama](https://img.shields.io/badge/AI-Ollama-white)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Vue d'Ensemble

**ProAct** est une solution GMAO moderne conçue pour l'industrie 4.0. Elle combine une gestion rigoureuse des actifs industriels avec des capacités d'intelligence artificielle avancées (RAG, Copilot, OCR, Prédiction) pour optimiser la maintenance préventive et corrective.

L'objectif est de réduire les temps d'arrêt non planifiés en fournissant aux techniciens et superviseurs des outils d'aide à la décision basés sur les données.

![Dashboard Preview](docs/assets/dashboard-preview.png)

## Architecture du Système

Le projet repose sur une architecture moderne et découplée, facilitant la maintenabilité et l'évolutivité.

```mermaid
graph TD
    subgraph Frontend ["Frontend Layer (Next.js 14)"]
        UI[Interface Utilisateur]
        Auth[Supabase Auth]
    end

    subgraph Backend ["Backend Layer (FastAPI)"]
        API[API Gateway]
        Services[Services Métier]
        
        subgraph AI_Modules ["Modules IA"]
            Copilot[Maintenance Copilot]
            RAG[RAG System]
            Predict[Prediction Engine]
            OCR[OCR Vision]
        end
    end

    subgraph Data ["Data Layer"]
        DB[(PostgreSQL)]
        VectorDB[(FAISS Vector Store)]
        Redis[(Redis Cache)]
    end

    subgraph AI_Provider ["Inférence IA"]
        Ollama[Ollama / Groq]
    end

    UI -->|HTTPS/JSON| API
    Auth -.->|JWT| API
    API --> Services
    Services --> AI_Modules
    Services --> DB
    AI_Modules --> VectorDB
    AI_Modules --> Redis
    AI_Modules --> Ollama
```

## Fonctionnalités Clés

### Gestion Métier
- **Équipements** : Suivi du cycle de vie, hiérarchie, et historique des pannes.
- **Interventions** : Création, assignation et suivi des ordres de travail (OT).
- **Stock & Pièces** : Gestion des inventaires et alertes de seuil critique.
- **Techniciens** : Gestion des profils, compétences et plannings.
- **AMDEC** : Analyse des modes de défaillance, de leurs effets et de leur criticité (RPN).

### Intelligence Artificielle
- **Maintenance Copilot** : Assistant conversationnel pour diagnostiquer les pannes et suggérer des actions.
- **RAG (Retrieval-Augmented Generation)** : Interrogation en langage naturel de la documentation technique (manuels PDF, historiques).
- **OCR Intelligent** : Extraction automatique de données depuis des rapports papiers ou plaques signalétiques.
- **Predictive Maintenance** : Prévision des pannes (MTBF) et estimation de la durée de vie restante (RUL) via Machine Learning.

## Flux de Données (Data Flow)

Le diagramme suivant illustre le flux de traitement d'une requête d'assistance technique par le système RAG :

```mermaid
sequenceDiagram
    participant User as Technicien
    participant UI as Frontend
    participant API as Backend API
    participant VS as Vector Store
    participant LLM as LLM (Ollama/Groq)

    User->>UI: Pose une question technique
    UI->>API: POST /api/rag/query
    API->>VS: Recherche similarité (Embeddings)
    VS-->>API: Retourne documents pertinents
    API->>LLM: Prompt (Question + Contexte)
    LLM-->>API: Réponse générée
    API-->>UI: Réponse structurée + Sources
    UI-->>User: Affiche la solution
```

## Installation & Démarrage

### Prérequis Technique
- **Runtime** : Node.js 18+ & pnpm
- **Langage** : Python 3.11+
- **Infrastructure** : Docker (recommandé pour la base de données et services IA)

### 1. Configuration Backend

```bash
cd backend
python -m venv venv
# Activation (Windows)
.\venv\Scripts\activate
# Activation (Linux/Mac)
source venv/bin/activate

pip install -r requirements.txt

# Configuration des variables d'environnement
cp .env.example .env
# Éditer .env avec les identifiants base de données
```

### 2. Configuration Frontend

```bash
cd frontend
pnpm install

# Configuration env
cp apps/web/.env.local.example apps/web/.env.local

# Lancement en mode développement
pnpm dev
```

## Configuration IA (Hybride)

Le système supporte le basculement entre inférence locale et cloud :

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `ollama` (local, privé) ou `groq` (cloud, rapide) |
| `OLLAMA_BASE_URL` | URL de l'instance Ollama (défaut : `http://localhost:11434`) |
| `GROQ_API_KEY` | Clé API requise si le provider est défini sur `groq` |

## Documentation

La documentation technique détaillée est disponible au format PDF dans le dossier `docs/`.

## Crédits

**Auteurs** : Mohamed Amine Darraj, Adam Khald  
**Encadrement** : Mr Tawfik Masrour, Mme Ibtissam Elhassani  

*Projet Académique - Génie Industriel*
