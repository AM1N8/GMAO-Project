# ProAct GMAO - Pipeline de Données

Ce document détaille l'architecture des données, les processus de nettoyage, et les stratégies d'intégration temps réel pour le système ProAct.

## Sources de Données (Datasets)

Les données historiques utilisées pour l'entraînement des modèles IA sont stockées dans ce dossier `data/`.

### 1. Analyse AMDEC (`AMDEC_clean.csv`)
Données relatives à la fiabilité et aux risques.
*   **Usage** : Entraînement du modèle de criticité (Predictive Maintenance).

### 2. Historique GMAO (`GMAO_integrator_clean.csv`)
Journal complet des interventions passées.
*   **Usage** : Base de connaissances pour le RAG et le Copilot.

### 3. Charge de Travail (`Workload_clean.csv`)
Données opérationnelles sur les techniciens.
*   **Usage** : Optimisation des plannings.

## Pré-traitement (Data Preprocessing)

Les scripts de nettoyage (`analyze_data.py`, etc.) assurent la qualité des données avant injection :

1.  **Nettoyage** :
    *   Gestion des valeurs manquantes (imputation par la moyenne ou suppression sur les colonnes critiques).
    *   Normalisation des dates (ISO 8601).
    *   Correction des encodages (Latin-1 -> UTF-8).
2.  **Feature Engineering** :
    *   Calcul automatique du RPN si manquant.
    *   Encodage des variables catégorielles (One-Hot Encoding pour les types de machines).
3.  **Split** : Séparation Train/Test (80/20) pour les modèles ML.

## Intégration Flux Temps Réel (Real-Time Stream)

Pour passer d'un mode "Batch" à un mode "Temps Réel" (ex: capteurs IoT sur machines), voici l'architecture recommandée à implémenter :

### Architecture Cible

```mermaid
graph LR
    Sensors[Capteurs IoT] -->|MQTT| Broker[MQTT Broker]
    Broker -->|Sub| Ingest[Service Ingestion (Python)]
    Ingest -->|Write| Redis[(Redis Stream)]
    Ingest -->|Archive| DB[(PostgreSQL)]
    
    Processing[FastAPI Worker] -->|Read| Redis
    Processing -->|Detect| Anomaly[Modèle Détection Anomalie]
    Anomaly -->|Alert| Frontend[Dashboard WebSocket]
```

### Étapes d'Implémentation

#### 1. Ingestion de Données (MQTT)
Utiliser un broker comme mosquito ou HiveMQ. Les capteurs envoient des payloads JSON :

```json
{
  "equipement_id": "PUMP-01",
  "temperature": 85.4,
  "vibration": 12.3,
  "timestamp": "2024-03-20T10:00:00Z"
}
```

#### 2. Service Consommateur (Backend)
Ajouter un service d'écoute dans `backend/app/services/iot_service.py` :

```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    # 1. Sauvegarder en DB
    save_telemetry(data)
    # 2. Vérifier seuils critiques (Anomaly Detection)
    if data['temperature'] > 90:
        trigger_alert(data)
```

#### 3. Diffusion Frontend (WebSockets)
Utiliser les WebSockets de FastAPI pour pousser les alertes vers le dashboard sans rechargement.

```python
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        alert = await redis.pop_alert()
        await websocket.send_json(alert)
```

## Flux de Mise à Jour IA

L'intégration temps réel permet le **Re-training continu** :
1.  Les nouvelles données capteurs enrichissent le dataset historique.
2.  Un pipeline (Airflow/Cron) déclenche le ré-entraînement du modèle `RandomForest` chaque semaine.
3.  Le nouveau modèle (`.pkl`) est déployé à chaud via l'API.
