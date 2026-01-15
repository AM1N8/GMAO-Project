"""
data_finetune/generators/qa_generator.py

Generate Question-Answering pairs from GMAO data.
"""

import pandas as pd
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta


class QAGenerator:
    """Generate diverse QA pairs."""
    
    def __init__(self, amdec_df: pd.DataFrame, dispo_df: pd.DataFrame, workload_df: pd.DataFrame):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 3000) -> List[Dict[str, Any]]:
        """Generate all types of QA pairs."""
        
        samples = []
        
        # Distribution of QA types
        n_factual = int(n_samples * 0.30)
        n_statistical = int(n_samples * 0.25)
        n_diagnostic = int(n_samples * 0.20)
        n_temporal = int(n_samples * 0.15)
        n_cost = int(n_samples * 0.10)
        
        samples.extend(self._generate_factual_qa(n_factual))
        samples.extend(self._generate_statistical_qa(n_statistical))
        samples.extend(self._generate_diagnostic_qa(n_diagnostic))
        samples.extend(self._generate_temporal_qa(n_temporal))
        samples.extend(self._generate_cost_qa(n_cost))
        
        random.shuffle(samples)
        return samples[:n_samples]
    
    def _generate_factual_qa(self, n: int) -> List[Dict[str, Any]]:
        """Generate factual QA pairs."""
        samples = []
        
        for _ in range(n):
            if len(self.amdec) == 0:
                break
                
            row = self.amdec.sample(1).iloc[0]
            
            templates = [
                {
                    "q": f"Quelle était la cause de la panne sur {row.get('Désignation', 'la machine')} le {row.get('Date intervention', '')}?",
                    "a": f"La cause était: {row.get('Cause', 'Non spécifiée')}"
                },
                {
                    "q": f"Quel type de panne s'est produit sur {row.get('Désignation', 'la machine')} le {row.get('Date intervention', '')}?",
                    "a": f"Type de panne: {row.get('Type de panne', 'Non spécifié')}"
                },
                {
                    "q": f"Quel organe était concerné par l'intervention sur {row.get('Désignation', 'la machine')} le {row.get('Date intervention', '')}?",
                    "a": f"Organe concerné: {row.get('Organe', 'Non spécifié')}"
                },
                {
                    "q": f"Quelle a été la durée d'arrêt pour l'intervention sur {row.get('Désignation', 'la machine')} le {row.get('Date intervention', '')}?",
                    "a": f"Durée d'arrêt: {row.get('Durée arrêt (h)', 0)} heures"
                },
                {
                    "q": f"Décris le résumé de l'intervention sur {row.get('Désignation', 'la machine')} le {row.get('Date intervention', '')}.",
                    "a": f"{row.get('Résumé intervention', 'Pas de résumé disponible')}"
                }
            ]
            
            template = random.choice(templates)
            
            samples.append({
                "instruction": "Réponds à la question suivante basée sur les données GMAO.",
                "input": template["q"],
                "output": template["a"]
            })
        
        return samples
    
    def _generate_statistical_qa(self, n: int) -> List[Dict[str, Any]]:
        """Generate statistical QA pairs."""
        samples = []
        
        for _ in range(n):
            templates = [
                self._count_failures_by_type,
                self._count_failures_by_machine,
                self._avg_downtime_by_type,
                self._total_cost_by_period,
                self._count_failures_by_cause
            ]
            
            generator = random.choice(templates)
            try:
                sample = generator()
                if sample:
                    samples.append(sample)
            except:
                continue
        
        return samples
    
    def _count_failures_by_type(self) -> Dict[str, Any]:
        """Count failures by type."""
        if 'Type de panne' not in self.amdec.columns:
            return None
        
        failure_type = self.amdec['Type de panne'].value_counts().index[0]
        count = self.amdec['Type de panne'].value_counts().iloc[0]
        
        return {
            "instruction": "Calcule les statistiques suivantes à partir des données GMAO.",
            "input": f"Combien de pannes de type '{failure_type}' ont été enregistrées?",
            "output": f"Il y a eu {count} pannes de type '{failure_type}' enregistrées dans le système."
        }
    
    def _count_failures_by_machine(self) -> Dict[str, Any]:
        """Count failures by machine."""
        if 'Désignation' not in self.amdec.columns:
            return None
        
        machine = self.amdec['Désignation'].value_counts().index[0]
        count = self.amdec['Désignation'].value_counts().iloc[0]
        
        return {
            "instruction": "Analyse les données de maintenance et réponds à la question.",
            "input": f"Combien d'interventions ont été effectuées sur {machine}?",
            "output": f"{machine} a nécessité {count} interventions de maintenance."
        }
    
    def _avg_downtime_by_type(self) -> Dict[str, Any]:
        """Average downtime by failure type."""
        if 'Type de panne' not in self.amdec.columns or 'Durée arrêt (h)' not in self.amdec.columns:
            return None
        
        failure_type = random.choice(self.amdec['Type de panne'].dropna().unique())
        avg_time = self.amdec[self.amdec['Type de panne'] == failure_type]['Durée arrêt (h)'].mean()
        
        return {
            "instruction": "Calcule la statistique demandée.",
            "input": f"Quelle est la durée moyenne d'arrêt pour les pannes de type '{failure_type}'?",
            "output": f"La durée moyenne d'arrêt pour les pannes '{failure_type}' est de {avg_time:.2f} heures."
        }
    
    def _total_cost_by_period(self) -> Dict[str, Any]:
        """Total cost by time period."""
        if 'Coût matériel' not in self.amdec.columns:
            return None
        
        total_cost = self.amdec['Coût matériel'].sum()
        
        return {
            "instruction": "Réponds à la question sur les coûts de maintenance.",
            "input": "Quel est le coût total en matériel pour toutes les interventions?",
            "output": f"Le coût total en matériel s'élève à {total_cost:.2f} unités monétaires."
        }
    
    def _count_failures_by_cause(self) -> Dict[str, Any]:
        """Count failures by cause."""
        if 'Cause' not in self.amdec.columns:
            return None
        
        cause = random.choice(self.amdec['Cause'].dropna().unique())
        count = len(self.amdec[self.amdec['Cause'] == cause])
        
        return {
            "instruction": "Analyse les causes de pannes.",
            "input": f"Combien de pannes ont été causées par '{cause}'?",
            "output": f"{count} pannes ont été identifiées avec la cause '{cause}'."
        }
    
    def _generate_diagnostic_qa(self, n: int) -> List[Dict[str, Any]]:
        """Generate diagnostic QA pairs."""
        samples = []
        
        for _ in range(n):
            if len(self.amdec) == 0:
                break
            
            row = self.amdec.sample(1).iloc[0]
            
            templates = [
                {
                    "q": f"Quels sont les symptômes typiques pour une panne '{row.get('Type de panne', 'inconnue')}'?",
                    "a": f"Pour les pannes de type '{row.get('Type de panne', 'inconnue')}', on observe généralement des problèmes au niveau de l'organe '{row.get('Organe', 'non spécifié')}'. L'intervention type consiste en: {row.get('Résumé intervention', 'vérifications standards')}."
                },
                {
                    "q": f"Quelle est la cause la plus probable quand on observe '{row.get('Cause', 'un problème')}'?",
                    "a": f"Cause identifiée: {row.get('Cause', 'À diagnostiquer')}. Le type de panne associé est généralement '{row.get('Type de panne', 'variable')}' affectant l'organe '{row.get('Organe', 'à déterminer')}'."
                }
            ]
            
            template = random.choice(templates)
            
            samples.append({
                "instruction": "En tant qu'expert GMAO, réponds à cette question de diagnostic.",
                "input": template["q"],
                "output": template["a"]
            })
        
        return samples
    
    def _generate_temporal_qa(self, n: int) -> List[Dict[str, Any]]:
        """Generate temporal QA pairs."""
        samples = []
        
        for _ in range(n):
            if 'Date intervention' not in self.amdec.columns or 'Désignation' not in self.amdec.columns:
                continue
            
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine].copy()
            
            if len(machine_data) == 0:
                continue
            
            machine_data['Date intervention'] = pd.to_datetime(machine_data['Date intervention'], errors='coerce')
            machine_data = machine_data.dropna(subset=['Date intervention'])
            
            if len(machine_data) < 2:
                continue
            
            machine_data = machine_data.sort_values('Date intervention')
            date_range = f"{machine_data['Date intervention'].min().strftime('%d/%m/%Y')} et {machine_data['Date intervention'].max().strftime('%d/%m/%Y')}"
            
            interventions = []
            for _, row in machine_data.head(5).iterrows():
                interventions.append(
                    f"- {row['Date intervention'].strftime('%d/%m/%Y')}: {row.get('Type de panne', 'N/A')} - {row.get('Résumé intervention', 'N/A')[:100]}"
                )
            
            samples.append({
                "instruction": "Liste les interventions pour la période demandée.",
                "input": f"Quelles interventions ont été effectuées sur {machine} entre {date_range}?",
                "output": f"Interventions sur {machine}:\n" + "\n".join(interventions)
            })
        
        return samples
    
    def _generate_cost_qa(self, n: int) -> List[Dict[str, Any]]:
        """Generate cost analysis QA pairs."""
        samples = []
        
        for _ in range(n):
            if 'Type de panne' not in self.amdec.columns or 'Coût matériel' not in self.amdec.columns:
                continue
            
            failure_type = random.choice(self.amdec['Type de panne'].dropna().unique())
            type_data = self.amdec[self.amdec['Type de panne'] == failure_type]
            
            total_cost = type_data['Coût matériel'].sum()
            count = len(type_data)
            avg_cost = total_cost / count if count > 0 else 0
            
            samples.append({
                "instruction": "Analyse les coûts de maintenance.",
                "input": f"Quel est le coût total et moyen pour les pannes de type '{failure_type}'?",
                "output": f"Pour les pannes '{failure_type}':\n- Coût total: {total_cost:.2f}\n- Nombre d'incidents: {count}\n- Coût moyen par incident: {avg_cost:.2f}"
            })
        
        return samples