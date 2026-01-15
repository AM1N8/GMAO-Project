"""
data_finetune/generators/advanced_generators.py

Diagnostic, Comparison, TimeSeries, MultiDoc, Conversation, Validation, Documentation generators.
"""

import pandas as pd
import random
from typing import List, Dict, Any
import numpy as np


class DiagnosticGenerator:
    """Generate diagnostic reasoning chains."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 400) -> List[Dict[str, Any]]:
        samples = []
        for _ in range(n_samples):
            row = self.amdec.sample(1).iloc[0]
            
            diagnostic = f"""DIAGNOSTIC TECHNIQUE

SYMPTÔMES OBSERVÉS:
- Type: {row.get('Type de panne', 'N/A')}
- Machine: {row.get('Désignation', 'N/A')}
- Organe affecté: {row.get('Organe', row.get('[Pièce].Désignation', 'N/A'))}

ANALYSE:
{row.get('Cause', 'Analyse en cours')}

INTERVENTION:
{row.get('Résumé intervention', 'À définir')}

RÉSULTAT:
- Durée: {row.get('Durée arrêt (h)', 0)}h
- Coût: {row.get('Coût matériel', 0)}"""
            
            samples.append({
                "instruction": f"Fournis un diagnostic technique détaillé pour cette panne sur {row.get('Désignation', 'N/A')}.",
                "input": f"Type: {row.get('Type de panne', 'N/A')}\nOrgane: {row.get('Organe', row.get('[Pièce].Désignation', 'N/A'))}",
                "output": diagnostic.strip()
            })
        
        return samples


class ComparisonGenerator:
    """Generate comparison and benchmarking tasks."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 300) -> List[Dict[str, Any]]:
        samples = []
        
        for _ in range(n_samples):
            machines = random.sample(list(self.amdec['Désignation'].dropna().unique()), min(2, len(self.amdec['Désignation'].unique())))
            
            if len(machines) < 2:
                continue
            
            m1_data = self.amdec[self.amdec['Désignation'] == machines[0]]
            m2_data = self.amdec[self.amdec['Désignation'] == machines[1]]
            
            comparison = f"""COMPARAISON: {machines[0]} vs {machines[1]}

{machines[0]}:
- Interventions: {len(m1_data)}
- Temps d'arrêt total: {m1_data['Durée arrêt (h)'].sum():.2f}h
- Coût total: {m1_data['Coût matériel'].sum():.2f}
- Temps d'arrêt moyen: {m1_data['Durée arrêt (h)'].mean():.2f}h

{machines[1]}:
- Interventions: {len(m2_data)}
- Temps d'arrêt total: {m2_data['Durée arrêt (h)'].sum():.2f}h
- Coût total: {m2_data['Coût matériel'].sum():.2f}
- Temps d'arrêt moyen: {m2_data['Durée arrêt (h)'].mean():.2f}h

CONCLUSION:
{machines[0] if len(m1_data) < len(m2_data) else machines[1]} est plus fiable avec moins d'interventions."""
            
            samples.append({
                "instruction": f"Compare la fiabilité et les coûts de maintenance entre {machines[0]} et {machines[1]}.",
                "input": "",
                "output": comparison.strip()
            })
        
        return samples


class TimeSeriesGenerator:
    """Generate time-series analysis tasks."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 300) -> List[Dict[str, Any]]:
        samples = []
        
        if 'Date intervention' not in self.amdec.columns:
            return samples
        
        self.amdec['Date intervention'] = pd.to_datetime(self.amdec['Date intervention'], errors='coerce')
        self.amdec = self.amdec.dropna(subset=['Date intervention'])
        
        for _ in range(n_samples):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine].sort_values('Date intervention')
            
            if len(machine_data) < 3:
                continue
            
            # Monthly trend
            machine_data['Month'] = machine_data['Date intervention'].dt.to_period('M')
            monthly = machine_data.groupby('Month').size()
            
            trend = "TENDANCE TEMPORELLE\n\n"
            trend += f"Analyse pour {machine}:\n\n"
            
            for month, count in monthly.head(6).items():
                trend += f"{month}: {count} interventions\n"
            
            if len(monthly) > 1:
                if monthly.iloc[-1] > monthly.iloc[0]:
                    trend += "\nTendance: AUGMENTATION des pannes"
                else:
                    trend += "\nTendance: DIMINUTION des pannes"
            
            samples.append({
                "instruction": f"Analyse l'évolution temporelle des pannes sur {machine}. Identifie les tendances.",
                "input": "",
                "output": trend.strip()
            })
        
        return samples


class MultiDocGenerator:
    """Generate multi-document reasoning tasks."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 500) -> List[Dict[str, Any]]:
        samples = []
        
        for _ in range(n_samples):
            if len(self.amdec) == 0 or len(self.workload) == 0:
                break
            
            # Find matching intervention
            amdec_row = self.amdec.sample(1).iloc[0]
            date = amdec_row.get('Date intervention')
            machine = amdec_row.get('Désignation')
            
            # Try to find workload data
            workload_match = self.workload[
                (self.workload['Date intervention'] == date) & 
                (self.workload['Désignation'] == machine)
            ]
            
            analysis = f"""ANALYSE COMPLÈTE

DONNÉES INTERVENTION (AMDEC):
- Machine: {machine}
- Date: {date}
- Type: {amdec_row.get('Type de panne', 'N/A')}
- Durée: {amdec_row.get('Durée arrêt (h)', 0)}h
- Coût matériel: {amdec_row.get('Coût matériel', 0)}

"""
            
            if len(workload_match) > 0:
                w_row = workload_match.iloc[0]
                labor_hours = w_row.get('Nombre d\'heures MO', 0)
                total_cost = w_row.get('Coût total intervention', 0)
                
                analysis += f"""DONNÉES MAIN D'ŒUVRE (WORKLOAD):
- Heures MO: {labor_hours}h
- Coût total: {total_cost}
- Techniciens: {w_row.get('[MO interne].Prénom', 'N/A')}

COÛT TOTAL RÉEL:
Matériel + Main d'œuvre = {amdec_row.get('Coût matériel', 0) + total_cost:.2f}"""
            
            samples.append({
                "instruction": f"Combine les données AMDEC et Workload pour cette intervention. Calcule le coût total.",
                "input": f"Date: {date}, Machine: {machine}",
                "output": analysis.strip()
            })
        
        return samples


class ConversationGenerator:
    """Generate multi-turn conversations."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 250) -> List[Dict[str, Any]]:
        samples = []
        
        for _ in range(n_samples):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            conversation = []
            
            # Turn 1
            conversation.append({
                "role": "user",
                "content": f"Parle-moi de {machine}"
            })
            conversation.append({
                "role": "assistant",
                "content": f"{machine} a enregistré {len(machine_data)} interventions avec un temps d'arrêt total de {machine_data['Durée arrêt (h)'].sum():.2f}h."
            })
            
            # Turn 2
            conversation.append({
                "role": "user",
                "content": "Quels sont les problèmes récurrents?"
            })
            
            top_failure = machine_data['Type de panne'].mode()
            if len(top_failure) > 0:
                failure = top_failure.iloc[0]
                count = len(machine_data[machine_data['Type de panne'] == failure])
                conversation.append({
                    "role": "assistant",
                    "content": f"Le problème le plus fréquent est '{failure}' avec {count} occurrences."
                })
            
            # Turn 3
            conversation.append({
                "role": "user",
                "content": "Recommande des actions préventives"
            })
            
            # Safe access to 'Organe'
            organe_val = 'N/A'
            if 'Organe' in machine_data.columns:
                modes = machine_data['Organe'].mode()
                if len(modes) > 0:
                    organe_val = modes[0]
            elif '[Pièce].Désignation' in machine_data.columns:
                modes = machine_data['[Pièce].Désignation'].mode()
                if len(modes) > 0:
                    organe_val = modes[0]
                    
            conversation.append({
                "role": "assistant",
                "content": f"Je recommande:\n1. Inspections mensuelles\n2. Surveillance accrue de l'organe '{organe_val}'\n3. Formation du personnel"
            })
            
            samples.append({
                "instruction": "Conversation multi-tours sur l'analyse de maintenance",
                "input": "",
                "output": "",
                "conversation": conversation
            })
        
        return samples


class ValidationGenerator:
    """Generate data validation tasks."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 200) -> List[Dict[str, Any]]:
        samples = []
        
        for _ in range(n_samples):
            row = self.amdec.sample(1).iloc[0]
            
            issues = []
            
            # Check for missing data
            if pd.isna(row.get('Cause')):
                issues.append("- Cause manquante")
            if row.get('Durée arrêt (h)', 0) == 0:
                issues.append("- Durée d'arrêt = 0 (suspect)")
            if row.get('Coût matériel', 0) > 5000:
                issues.append("- Coût anormalement élevé (>5000)")
            
            if issues:
                validation = f"""VALIDATION DES DONNÉES

Intervention: {row.get('Date intervention', 'N/A')} - {row.get('Désignation', 'N/A')}

PROBLÈMES DÉTECTÉS:
""" + "\n".join(issues) + "\n\nACTIONS: Vérifier et compléter les données"
            else:
                validation = "VALIDATION: Données complètes et cohérentes"
            
            samples.append({
                "instruction": "Valide la qualité et la cohérence de ces données d'intervention.",
                "input": f"Machine: {row.get('Désignation', 'N/A')}\nDurée: {row.get('Durée arrêt (h)', 0)}h\nCoût: {row.get('Coût matériel', 0)}",
                "output": validation.strip()
            })
        
        return samples


class DocumentationGenerator:
    """Generate technical documentation."""
    
    def __init__(self, amdec_df, dispo_df, workload_df):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 150) -> List[Dict[str, Any]]:
        samples = []
        
        for _ in range(n_samples):
            failure_type = random.choice(self.amdec['Type de panne'].dropna().unique())
            type_data = self.amdec[self.amdec['Type de panne'] == failure_type]
            
            # Get common interventions
            if 'Résumé intervention' in type_data.columns:
                interventions = type_data['Résumé intervention'].value_counts().head(3)
            else:
                interventions = pd.Series(["Maintenance corrective standard"], index=["Intervention"])
            
            doc = f"""PROCÉDURE: {failure_type}

DESCRIPTION:
Type de panne fréquent affectant les machines de production.

FRÉQUENCE:
{len(type_data)} occurrences enregistrées

DURÉE MOYENNE:
{type_data['Durée arrêt (h)'].mean():.2f} heures

INTERVENTIONS TYPES:
"""
            
            for i, (intervention, count) in enumerate(interventions.items(), 1):
                doc += f"\n{i}. {intervention[:100]}"
            
            doc += f"""

PIÈCES FRÉQUEMMENT UTILISÉES:
{type_data['[Pièce].Désignation'].value_counts().head(3).to_string() if '[Pièce].Désignation' in type_data.columns else 'N/A'}

COÛT MOYEN:
{type_data['Coût matériel'].mean():.2f}"""
            
            samples.append({
                "instruction": f"Génère une documentation technique standard pour les interventions de type '{failure_type}'.",
                "input": "",
                "output": doc.strip()
            })
        
        return samples