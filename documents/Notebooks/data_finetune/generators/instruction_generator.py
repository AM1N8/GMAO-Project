"""
data_finetune/generators/instruction_generator.py

Generate instruction-following tasks.
"""

import pandas as pd
import random
from typing import List, Dict, Any


class InstructionGenerator:
    """Generate instruction-following tasks."""
    
    def __init__(self, amdec_df: pd.DataFrame, dispo_df: pd.DataFrame, workload_df: pd.DataFrame):
        self.amdec = amdec_df
        self.dispo = dispo_df
        self.workload = workload_df
    
    def generate_all(self, n_samples: int = 800) -> List[Dict[str, Any]]:
        """Generate all instruction types."""
        
        samples = []
        
        generators = [
            (self._generate_sorting_tasks, 0.20),
            (self._generate_filtering_tasks, 0.20),
            (self._generate_report_tasks, 0.25),
            (self._generate_analysis_tasks, 0.20),
            (self._generate_calculation_tasks, 0.15)
        ]
        
        for generator, proportion in generators:
            n = int(n_samples * proportion)
            samples.extend(generator(n))
        
        random.shuffle(samples)
        return samples[:n_samples]
    
    def _generate_sorting_tasks(self, n: int) -> List[Dict[str, Any]]:
        """Generate sorting tasks."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine].copy()
            
            if len(machine_data) < 3:
                continue
            
            # Sort by downtime
            sorted_data = machine_data.nlargest(5, 'Durée arrêt (h)')
            
            result = f"Top 5 interventions par durée d'arrêt pour {machine}:\n\n"
            for i, (_, row) in enumerate(sorted_data.iterrows(), 1):
                result += f"{i}. {row.get('Date intervention', 'N/A')} - {row.get('Type de panne', 'N/A')}\n"
                result += f"   Durée: {row.get('Durée arrêt (h)', 0)} heures\n"
                result += f"   Cause: {row.get('Cause', 'N/A')}\n\n"
            
            samples.append({
                "instruction": f"Liste les interventions sur {machine} triées par durée d'arrêt décroissante. Limite aux 5 plus longues.",
                "input": "",
                "output": result.strip()
            })
        
        return samples
    
    def _generate_filtering_tasks(self, n: int) -> List[Dict[str, Any]]:
        """Generate filtering tasks."""
        samples = []
        
        for _ in range(n):
            failure_types = self.amdec['Type de panne'].dropna().unique()
            if len(failure_types) == 0:
                continue
            
            failure_type = random.choice(failure_types)
            filtered = self.amdec[self.amdec['Type de panne'] == failure_type]
            
            result = f"Interventions de type '{failure_type}' ({len(filtered)} résultats):\n\n"
            
            for _, row in filtered.head(10).iterrows():
                result += f"• {row.get('Désignation', 'N/A')} - {row.get('Date intervention', 'N/A')}\n"
                result += f"  Durée: {row.get('Durée arrêt (h)', 0)}h | Coût: {row.get('Coût matériel', 0)}\n"
                result += f"  Cause: {row.get('Cause', 'N/A')}\n\n"
            
            samples.append({
                "instruction": f"Filtre et affiche toutes les interventions de type '{failure_type}'. Inclus la machine, date, durée, coût et cause.",
                "input": "",
                "output": result.strip()
            })
        
        return samples
    
    def _generate_report_tasks(self, n: int) -> List[Dict[str, Any]]:
        """Generate report generation tasks."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            # Calculate statistics
            total_interventions = len(machine_data)
            total_downtime = machine_data['Durée arrêt (h)'].sum()
            total_cost = machine_data['Coût matériel'].sum()
            avg_downtime = machine_data['Durée arrêt (h)'].mean()
            
            # Most common failure
            if 'Type de panne' in machine_data.columns:
                most_common = machine_data['Type de panne'].mode()
                most_common_failure = most_common.iloc[0] if len(most_common) > 0 else 'N/A'
            else:
                most_common_failure = 'N/A'
            
            report = f"""RAPPORT DE MAINTENANCE - {machine}
{'='*50}

STATISTIQUES GÉNÉRALES:
- Nombre total d'interventions: {total_interventions}
- Temps d'arrêt total: {total_downtime:.2f} heures
- Coût matériel total: {total_cost:.2f}
- Durée moyenne d'arrêt: {avg_downtime:.2f} heures

TYPE DE PANNE LE PLUS FRÉQUENT:
- {most_common_failure}

INTERVENTIONS RÉCENTES:
"""
            
            for _, row in machine_data.head(5).iterrows():
                report += f"\n• {row.get('Date intervention', 'N/A')} - {row.get('Type de panne', 'N/A')}"
                report += f"\n  Durée: {row.get('Durée arrêt (h)', 0)}h | Cause: {row.get('Cause', 'N/A')}"
            
            samples.append({
                "instruction": f"Génère un rapport de maintenance complet pour {machine}. Inclus statistiques, types de pannes fréquents et liste des interventions récentes.",
                "input": "",
                "output": report.strip()
            })
        
        return samples
    
    def _generate_analysis_tasks(self, n: int) -> List[Dict[str, Any]]:
        """Generate analysis tasks."""
        samples = []
        
        for _ in range(n):
            # Analyze failure patterns
            failure_counts = self.amdec['Type de panne'].value_counts().head(5)
            
            analysis = "ANALYSE DES PANNES:\n\n"
            analysis += "Les 5 types de pannes les plus fréquents sont:\n\n"
            
            for i, (failure_type, count) in enumerate(failure_counts.items(), 1):
                percentage = (count / len(self.amdec)) * 100
                analysis += f"{i}. {failure_type}: {count} occurrences ({percentage:.1f}%)\n"
                
                # Get average downtime for this type
                type_data = self.amdec[self.amdec['Type de panne'] == failure_type]
                avg_time = type_data['Durée arrêt (h)'].mean()
                analysis += f"   Durée moyenne d'arrêt: {avg_time:.2f}h\n\n"
            
            analysis += "\nRECOMMANDATIONS:\n"
            analysis += f"- Prioriser la prévention pour '{failure_counts.index[0]}' (type le plus fréquent)\n"
            analysis += "- Mettre en place des contrôles réguliers sur les organes critiques\n"
            analysis += "- Former le personnel sur les pannes récurrentes\n"
            
            samples.append({
                "instruction": "Analyse les patterns de pannes dans le système. Identifie les types les plus fréquents, leur impact, et fournis des recommandations.",
                "input": "",
                "output": analysis.strip()
            })
        
        return samples
    
    def _generate_calculation_tasks(self, n: int) -> List[Dict[str, Any]]:
        """Generate calculation tasks."""
        samples = []
        
        for _ in range(n):
            machine = random.choice(self.amdec['Désignation'].dropna().unique())
            machine_data = self.amdec[self.amdec['Désignation'] == machine]
            
            # Calculate MTBF and MTTR
            total_time = 365 * 24  # Assume 1 year in hours
            total_downtime = machine_data['Durée arrêt (h)'].sum()
            num_failures = len(machine_data)
            
            mtbf = (total_time - total_downtime) / num_failures if num_failures > 0 else 0
            mttr = total_downtime / num_failures if num_failures > 0 else 0
            availability = ((total_time - total_downtime) / total_time) * 100
            
            result = f"""CALCULS DE FIABILITÉ - {machine}
{'='*50}

MÉTRIQUES CALCULÉES:

1. MTBF (Mean Time Between Failures):
   {mtbf:.2f} heures
   
   Calcul: (Temps total - Temps d'arrêt) / Nombre de pannes
   = ({total_time} - {total_downtime:.2f}) / {num_failures}
   = {mtbf:.2f} heures

2. MTTR (Mean Time To Repair):
   {mttr:.2f} heures
   
   Calcul: Temps d'arrêt total / Nombre de pannes
   = {total_downtime:.2f} / {num_failures}
   = {mttr:.2f} heures

3. DISPONIBILITÉ:
   {availability:.2f}%
   
   Calcul: (Temps opérationnel / Temps total) × 100
   = (({total_time} - {total_downtime:.2f}) / {total_time}) × 100
   = {availability:.2f}%

INTERPRÉTATION:
- MTBF élevé = Bonne fiabilité
- MTTR faible = Maintenance efficace
- Disponibilité > 95% = Excellent
"""
            
            samples.append({
                "instruction": f"Calcule les indicateurs de fiabilité (MTBF, MTTR, Disponibilité) pour {machine}. Montre les calculs détaillés et interprète les résultats.",
                "input": "",
                "output": result.strip()
            })
        
        return samples