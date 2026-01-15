"""
data_finetune/generators/simple_generators.py

Classification, Summarization, and Prediction generators.
"""

import pandas as pd
import random
from typing import List, Dict, Any
import numpy as np


class ClassificationGenerator:
    """Generate classification tasks."""
    
    def __init__(self, amdec_df: pd.DataFrame, dispo_df: pd.DataFrame, workload_df: pd.DataFrame):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 500) -> List[Dict[str, Any]]:
        """Generate classification tasks."""
        samples = []
        
        generators = [
            (self._classify_severity, 0.30),
            (self._classify_urgency, 0.25),
            (self._classify_failure_pattern, 0.25),
            (self._classify_maintenance_type, 0.20)
        ]
        
        for generator, proportion in generators:
            n = int(n_samples * proportion)
            samples.extend(generator(n))
        
        random.shuffle(samples)
        return samples[:n_samples]
    
    def _classify_severity(self, n: int) -> List[Dict[str, Any]]:
        """Classify failure severity."""
        samples = []
        
        for _ in range(n):
            if len(self.amdec) == 0:
                break
            
            row = self.amdec.sample(1).iloc[0]
            downtime = row.get('Durée arrêt (h)', 0)
            cost = row.get('Coût matériel', 0)
            
            # Classification logic
            if downtime > 100 or cost > 1000:
                severity = "CRITIQUE"
                explanation = f"Temps d'arrêt de {downtime}h et coût de {cost} indiquent une panne critique nécessitant une attention immédiate."
            elif downtime > 10 or cost > 200:
                severity = "ÉLEVÉE"
                explanation = f"Avec {downtime}h d'arrêt et un coût de {cost}, cette panne a un impact significatif sur la production."
            elif downtime > 1 or cost > 50:
                severity = "MOYENNE"
                explanation = f"Impact modéré: {downtime}h d'arrêt et coût de {cost}. Maintenance planifiable."
            else:
                severity = "FAIBLE"
                explanation = f"Panne mineure: {downtime}h d'arrêt, coût de {cost}. Impact limité."
            
            context = f"""Type de panne: {row.get('Type de panne', 'N/A')}
Machine: {row.get('Désignation', 'N/A')}
Durée d'arrêt: {downtime} heures
Coût matériel: {cost}
Cause: {row.get('Cause', 'N/A')}"""
            
            samples.append({
                "instruction": "Classifie la sévérité de cette panne (CRITIQUE, ÉLEVÉE, MOYENNE, FAIBLE) et explique ton raisonnement.",
                "input": context,
                "output": f"Sévérité: {severity}\n\nExplication: {explanation}"
            })
        
        return samples
    
    def _classify_urgency(self, n: int) -> List[Dict[str, Any]]:
        """Classify maintenance urgency."""
        samples = []
        
        for _ in range(n):
            if len(self.amdec) == 0:
                break
            
            row = self.amdec.sample(1).iloc[0]
            failure_type = row.get('Type de panne', '')
            cause = row.get('Cause', '')
            
            # Urgency classification
            critical_keywords = ['BLOCAGE', 'HS', 'CASSE', 'ARRET']
            high_keywords = ['PROBLEME', 'DEFAUT', 'PANNE']
            
            if any(keyword in str(cause).upper() for keyword in critical_keywords):
                urgency = "IMMÉDIATE"
                action = "Intervention requise dans l'heure. Arrêt de production imminent."
            elif any(keyword in str(cause).upper() for keyword in high_keywords):
                urgency = "ÉLEVÉE"
                action = "Planifier l'intervention dans les 24h. Risque de dégradation."
            else:
                urgency = "NORMALE"
                action = "Maintenance planifiable. Intégrer au planning hebdomadaire."
            
            context = f"""Type: {failure_type}
Cause: {cause}
Organe: {row.get('Organe', 'N/A')}
Machine: {row.get('Désignation', 'N/A')}"""
            
            samples.append({
                "instruction": "Détermine le niveau d'urgence de cette intervention et recommande une action.",
                "input": context,
                "output": f"Urgence: {urgency}\n\nAction recommandée: {action}"
            })
        
        return samples
    
    def _classify_failure_pattern(self, n: int) -> List[Dict[str, Any]]:
        """Classify if failure is recurring."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            if len(machine_data) < 2:
                continue
            
            failure_counts = machine_data['Type de panne'].value_counts()
            most_common = failure_counts.index[0]
            count = failure_counts.iloc[0]
            
            if count >= 5:
                pattern = "RÉCURRENT"
                analysis = f"Le problème '{most_common}' s'est produit {count} fois. C'est un pattern récurrent nécessitant une analyse root cause et des actions préventives."
            elif count >= 3:
                pattern = "PRÉOCCUPANT"
                analysis = f"'{most_common}' apparaît {count} fois. Tendance à surveiller de près pour éviter la récurrence."
            else:
                pattern = "ISOLÉ"
                analysis = f"Les pannes semblent diverses et non récurrentes. Maintenance réactive appropriée."
            
            samples.append({
                "instruction": f"Analyse l'historique de {machine} et détermine s'il y a des patterns de pannes récurrents.",
                "input": f"Nombre d'interventions: {len(machine_data)}\nTypes de pannes observés: {', '.join(failure_counts.head(3).index.tolist())}",
                "output": f"Pattern identifié: {pattern}\n\nAnalyse: {analysis}"
            })
        
        return samples
    
    def _classify_maintenance_type(self, n: int) -> List[Dict[str, Any]]:
        """Classify type of maintenance needed."""
        samples = []
        
        maintenance_types = {
            "CORRECTIVE": ["réparation", "changement", "remplacement"],
            "PREVENTIVE": ["vérification", "contrôle", "nettoyage", "graissage"],
            "PREDICTIVE": ["analyse", "diagnostic", "surveillance"],
            "AMELIORATION": ["modification", "amélioration", "optimisation"]
        }
        
        for _ in range(n):
            if len(self.amdec) == 0:
                break
            
            row = self.amdec.sample(1).iloc[0]
            summary = str(row.get('Résumé intervention', '')).lower()
            
            maint_type = "CORRECTIVE"  # default
            for mtype, keywords in maintenance_types.items():
                if any(keyword in summary for keyword in keywords):
                    maint_type = mtype
                    break
            
            samples.append({
                "instruction": "Classifie le type de maintenance effectué (CORRECTIVE, PREVENTIVE, PREDICTIVE, AMELIORATION).",
                "input": f"Intervention: {row.get('Résumé intervention', 'N/A')}",
                "output": f"Type de maintenance: {maint_type}"
            })
        
        return samples


class SummarizationGenerator:
    """Generate summarization tasks."""
    
    def __init__(self, amdec_df: pd.DataFrame, dispo_df: pd.DataFrame, workload_df: pd.DataFrame):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 400) -> List[Dict[str, Any]]:
        """Generate summarization tasks."""
        samples = []
        
        generators = [
            (self._daily_summaries, 0.25),
            (self._weekly_summaries, 0.25),
            (self._machine_summaries, 0.25),
            (self._cost_summaries, 0.25)
        ]
        
        for generator, proportion in generators:
            n = int(n_samples * proportion)
            samples.extend(generator(n))
        
        random.shuffle(samples)
        return samples[:n_samples]
    
    def _daily_summaries(self, n: int) -> List[Dict[str, Any]]:
        """Generate daily summaries."""
        samples = []
        
        if 'Date intervention' not in self.amdec.columns:
            return samples
        
        self.amdec['Date intervention'] = pd.to_datetime(self.amdec['Date intervention'], errors='coerce')
        dates = self.amdec['Date intervention'].dropna().dt.date.unique()
        
        for date in random.sample(list(dates), min(n, len(dates))):
            day_data = self.amdec[self.amdec['Date intervention'].dt.date == date]
            
            summary = f"RÉSUMÉ QUOTIDIEN - {date}\n\n"
            summary += f"Total interventions: {len(day_data)}\n"
            summary += f"Temps d'arrêt total: {day_data['Durée arrêt (h)'].sum():.2f}h\n\n"
            summary += "Interventions:\n"
            
            for _, row in day_data.iterrows():
                summary += f"• {row.get('Désignation', 'N/A')}: {row.get('Type de panne', 'N/A')} ({row.get('Durée arrêt (h)', 0)}h)\n"
            
            samples.append({
                "instruction": f"Génère un résumé des interventions du {date}.",
                "input": "",
                "output": summary.strip()
            })
        
        return samples
    
    def _weekly_summaries(self, n: int) -> List[Dict[str, Any]]:
        """Generate weekly summaries."""
        samples = []
        
        for _ in range(n):
            # Sample a week of data
            sample_data = self.amdec.sample(min(20, len(self.amdec)))
            
            summary = "RÉSUMÉ HEBDOMADAIRE\n\n"
            summary += f"Interventions: {len(sample_data)}\n"
            summary += f"Temps d'arrêt: {sample_data['Durée arrêt (h)'].sum():.2f}h\n"
            summary += f"Coût matériel: {sample_data['Coût matériel'].sum():.2f}\n\n"
            
            # Top machines
            top_machines = sample_data['Désignation'].value_counts().head(3)
            summary += "Machines les plus sollicitées:\n"
            for machine, count in top_machines.items():
                summary += f"• {machine}: {count} interventions\n"
            
            samples.append({
                "instruction": "Crée un résumé hebdomadaire des activités de maintenance.",
                "input": "",
                "output": summary.strip()
            })
        
        return samples
    
    def _machine_summaries(self, n: int) -> List[Dict[str, Any]]:
        """Generate machine status summaries."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            summary = f"ÉTAT DE {machine}\n\n"
            summary += f"Interventions: {len(machine_data)}\n"
            summary += f"Disponibilité estimée: {100 - (machine_data['Durée arrêt (h)'].sum() / 8760 * 100):.1f}%\n"
            summary += f"Coût maintenance: {machine_data['Coût matériel'].sum():.2f}\n\n"
            
            if 'Type de panne' in machine_data.columns:
                top_failure = machine_data['Type de panne'].mode()
                if len(top_failure) > 0:
                    summary += f"Panne récurrente: {top_failure.iloc[0]}\n"
            
            samples.append({
                "instruction": f"Résume l'état et l'historique de maintenance de {machine}.",
                "input": "",
                "output": summary.strip()
            })
        
        return samples
    
    def _cost_summaries(self, n: int) -> List[Dict[str, Any]]:
        """Generate cost breakdown summaries."""
        samples = []
        
        for _ in range(n):
            total_cost = self.amdec['Coût matériel'].sum()
            
            summary = "ANALYSE DES COÛTS\n\n"
            summary += f"Coût total: {total_cost:.2f}\n\n"
            
            # Cost by type
            cost_by_type = self.amdec.groupby('Type de panne')['Coût matériel'].sum().sort_values(ascending=False).head(5)
            summary += "Coûts par type de panne:\n"
            for ptype, cost in cost_by_type.items():
                pct = (cost / total_cost) * 100
                summary += f"• {ptype}: {cost:.2f} ({pct:.1f}%)\n"
            
            samples.append({
                "instruction": "Fournis une analyse détaillée des coûts de maintenance.",
                "input": "",
                "output": summary.strip()
            })
        
        return samples


class PredictionGenerator:
    """Generate predictive/analytical tasks."""
    
    def __init__(self, amdec_df: pd.DataFrame, dispo_df: pd.DataFrame, workload_df: pd.DataFrame):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 400) -> List[Dict[str, Any]]:
        """Generate prediction tasks."""
        samples = []
        
        generators = [
            (self._predict_next_failure, 0.30),
            (self._recommend_preventive, 0.30),
            (self._identify_risk_machines, 0.25),
            (self._predict_costs, 0.15)
        ]
        
        for generator, proportion in generators:
            n = int(n_samples * proportion)
            samples.extend(generator(n))
        
        random.shuffle(samples)
        return samples[:n_samples]
    
    def _predict_next_failure(self, n: int) -> List[Dict[str, Any]]:
        """Predict next likely failure."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            # Find most common failure
            most_common = machine_data['Type de panne'].mode()
            if len(most_common) == 0:
                continue
            
            failure_type = most_common.iloc[0]
            count = len(machine_data[machine_data['Type de panne'] == failure_type])
            probability = (count / len(machine_data)) * 100
            
            prediction = f"""PRÉDICTION DE PANNE - {machine}

Basé sur l'historique:
- {len(machine_data)} interventions enregistrées
- Type de panne le plus fréquent: {failure_type} ({count} occurrences)

PRÉDICTION:
La prochaine panne sera probablement de type '{failure_type}' avec une probabilité de {probability:.1f}%.

RECOMMANDATION:
- Inspecter régulièrement l'organe concerné
- Préparer les pièces de rechange nécessaires
- Former l'équipe sur cette intervention spécifique"""
            
            samples.append({
                "instruction": f"Basé sur l'historique, prédis le type de panne le plus probable sur {machine} et fournis des recommandations.",
                "input": "",
                "output": prediction.strip()
            })
        
        return samples
    
    def _recommend_preventive(self, n: int) -> List[Dict[str, Any]]:
        """Recommend preventive maintenance."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            avg_downtime = machine_data['Durée arrêt (h)'].mean()
            total_cost = machine_data['Coût matériel'].sum()
            
            recommendation = f"""PLAN DE MAINTENANCE PRÉVENTIVE - {machine}

ANALYSE:
- Temps d'arrêt moyen: {avg_downtime:.2f}h par incident
- Coût total historique: {total_cost:.2f}
- Nombre d'interventions: {len(machine_data)}

ACTIONS PRÉVENTIVES RECOMMANDÉES:

1. Inspections mensuelles
   - Vérifier les organes critiques
   - Contrôler les niveaux (huile, liquide)
   
2. Maintenance trimestrielle
   - Nettoyage complet
   - Remplacement des consommables
   
3. Révision annuelle
   - Vérification complète
   - Remplacement préventif des pièces d'usure

BÉNÉFICES ATTENDUS:
- Réduction de 30-40% du temps d'arrêt
- Diminution des coûts de réparation d'urgence
- Augmentation de la disponibilité"""
            
            samples.append({
                "instruction": f"Propose un plan de maintenance préventive pour {machine} basé sur son historique.",
                "input": "",
                "output": recommendation.strip()
            })
        
        return samples
    
    def _identify_risk_machines(self, n: int) -> List[Dict[str, Any]]:
        """Identify high-risk machines."""
        samples = []
        
        for _ in range(n):
            # Calculate risk scores
            machine_stats = self.amdec.groupby('Désignation').agg({
                'Durée arrêt (h)': 'sum',
                'Coût matériel': 'sum',
                'Type de panne': 'count'
            }).reset_index()
            
            machine_stats.columns = ['Machine', 'Total_Downtime', 'Total_Cost', 'Num_Failures']
            
            # Normalize and calculate risk score
            machine_stats['Risk_Score'] = (
                machine_stats['Total_Downtime'] / machine_stats['Total_Downtime'].max() +
                machine_stats['Total_Cost'] / machine_stats['Total_Cost'].max() +
                machine_stats['Num_Failures'] / machine_stats['Num_Failures'].max()
            ) / 3
            
            high_risk = machine_stats.nlargest(5, 'Risk_Score')
            
            analysis = "MACHINES À RISQUE ÉLEVÉ\n\n"
            analysis += "Top 5 machines nécessitant une attention prioritaire:\n\n"
            
            for i, row in high_risk.iterrows():
                analysis += f"{int(i)+1}. {row['Machine']}\n"
                analysis += f"   Score de risque: {row['Risk_Score']:.2f}/1.00\n"
                analysis += f"   Pannes: {int(row['Num_Failures'])} | Arrêt: {row['Total_Downtime']:.0f}h | Coût: {row['Total_Cost']:.0f}\n\n"
            
            samples.append({
                "instruction": "Identifie les machines à haut risque qui nécessitent une attention prioritaire. Calcule un score de risque basé sur la fréquence des pannes, temps d'arrêt et coûts.",
                "input": "",
                "output": analysis.strip()
            })
        
        return samples
    
    def _predict_costs(self, n: int) -> List[Dict[str, Any]]:
        """Predict future maintenance costs."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            avg_cost_per_intervention = machine_data['Coût matériel'].mean()
            interventions_per_period = len(machine_data)
            
            # Simple projection
            projected_cost = avg_cost_per_intervention * interventions_per_period
            
            prediction = f"""PRÉVISION DES COÛTS - {machine}

DONNÉES HISTORIQUES:
- Interventions: {interventions_per_period}
- Coût moyen/intervention: {avg_cost_per_intervention:.2f}
- Coût total passé: {machine_data['Coût matériel'].sum():.2f}

PROJECTION:
Coût estimé pour la prochaine période: {projected_cost:.2f}

RECOMMANDATION BUDGÉTAIRE:
- Budget minimal: {projected_cost * 0.8:.2f}
- Budget recommandé: {projected_cost * 1.2:.2f} (inclut marge de sécurité)
- Budget optimal: {projected_cost * 1.5:.2f} (inclut améliorations)"""
            
            samples.append({
                "instruction": f"Estime les coûts de maintenance futurs pour {machine} et recommande un budget.",
                "input": "",
                "output": prediction.strip()
            })
        
        return samples