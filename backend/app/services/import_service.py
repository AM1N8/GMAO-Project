"""
Import Service - Handles CSV imports for AMDEC, GMAO, and Workload datasets.
Provides encoding detection, date parsing, validation, and error handling.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
from typing import Dict, List, Tuple
import pandas as pd
import chardet
import io
import logging
import re

from app.models import (
    Equipment, Intervention, SparePart, Technician,
    InterventionPart, TechnicianAssignment, ImportLog,
    EquipmentStatus, TechnicianStatus, InterventionStatus
)

logger = logging.getLogger(__name__)


class ImportService:
    """Service class for CSV import operations"""
    
    @staticmethod
    def detect_encoding(file_content: bytes) -> str:
        """
        Detect file encoding using chardet
        
        Args:
            file_content: Raw file bytes
        
        Returns:
            Detected encoding string
        """
        result = chardet.detect(file_content)
        encoding = result['encoding']
        confidence = result['confidence']
        
        logger.info(f"Detected encoding: {encoding} (confidence: {confidence})")
        
        # Fallback to common encodings if confidence is low
        if confidence < 0.7:
            for fallback in ['windows-1252', 'utf-8', 'latin-1']:
                try:
                    file_content.decode(fallback)
                    encoding = fallback
                    logger.info(f"Using fallback encoding: {encoding}")
                    break
                except:
                    continue
        
        return encoding or 'utf-8'
    
    @staticmethod
    def clean_numeric(value) -> float:
        """
        Convert French decimal format to float
        Handles comma as decimal separator and removes spaces
        
        Args:
            value: Numeric value (string or number)
        
        Returns:
            Float value
        """
        if pd.isna(value):
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Convert to string and clean
        value_str = str(value).strip()
        
        # Remove spaces
        value_str = value_str.replace(' ', '')
        
        # Replace comma with period
        value_str = value_str.replace(',', '.')
        
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Could not convert '{value}' to float, returning 0.0")
            return 0.0
    
    @staticmethod
    def parse_french_date(date_str, include_time=False) -> date or datetime:
        """
        Parse French date format DD/MM/YYYY or DD/MM/YYYY HH:MM
        
        Args:
            date_str: Date string
            include_time: If True, parse as datetime
        
        Returns:
            date or datetime object
        """
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Try different formats
        formats = [
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if include_time:
                    return parsed
                else:
                    return parsed.date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @staticmethod
    def get_or_create_equipment(db: Session, designation: str) -> Equipment:
        """
        Get existing equipment or create new one
        
        Args:
            db: Database session
            designation: Equipment name
        
        Returns:
            Equipment object
        """
        equipment = db.query(Equipment).filter(
            Equipment.designation == designation
        ).first()
        
        if not equipment:
            equipment = Equipment(
                designation=designation,
                status=EquipmentStatus.ACTIVE
            )
            db.add(equipment)
            db.flush()  # Get ID without committing
            logger.info(f"Created new equipment: {designation}")
        
        return equipment
    
    @staticmethod
    def get_or_create_spare_part(
        db: Session,
        designation: str,
        reference: str,
        cout_unitaire: float = 0.0
    ) -> SparePart:
        """
        Get existing spare part or create new one
        
        Args:
            db: Database session
            designation: Part name
            reference: Part reference number
            cout_unitaire: Unit cost
        
        Returns:
            SparePart object
        """
        spare_part = db.query(SparePart).filter(
            SparePart.reference == reference
        ).first()
        
        if not spare_part:
            spare_part = SparePart(
                designation=designation,
                reference=reference,
                cout_unitaire=cout_unitaire,
                stock_actuel=0,
                seuil_alerte=10
            )
            db.add(spare_part)
            db.flush()
            logger.info(f"Created new spare part: {reference}")
        
        return spare_part
    
    @staticmethod
    def get_or_create_technician(
        db: Session,
        nom: str,
        prenom: str,
        taux_horaire: float = 50.0
    ) -> Technician:
        """
        Get existing technician or create new one
        
        Args:
            db: Database session
            nom: Last name
            prenom: First name
            taux_horaire: Hourly rate
        
        Returns:
            Technician object
        """
        # Generate email if not exists
        email = f"{prenom.lower()}.{nom.lower()}@company.com"
        
        technician = db.query(Technician).filter(
            Technician.nom == nom,
            Technician.prenom == prenom
        ).first()
        
        if not technician:
            technician = Technician(
                nom=nom,
                prenom=prenom,
                email=email,
                taux_horaire=taux_horaire,
                status=TechnicianStatus.ACTIVE
            )
            db.add(technician)
            db.flush()
            logger.info(f"Created new technician: {prenom} {nom}")
        
        return technician
    
    @staticmethod
    async def import_amdec_csv(
        db: Session,
        file_content: bytes,
        filename: str,
        user_id: str = "system"
    ) -> Dict:
        """
        Import AMDEC CSV file
        
        Expected columns:
        - Désignation (equipment)
        - Type de panne
        - Durée arrêt (h)
        - Date intervention
        - Date demande
        - Cause
        - Organe
        - Résumé intervention
        - Coût matériel
        
        Args:
            db: Database session
            file_content: File bytes
            filename: Original filename
            user_id: User performing import
        
        Returns:
            Dict with import statistics
        """
        start_time = datetime.now()
        errors = []
        successful_rows = 0
        failed_rows = 0
        
        try:
            # Detect encoding
            encoding = ImportService.detect_encoding(file_content)
            
            # Read CSV
            df = pd.read_csv(
                io.BytesIO(file_content),
                encoding=encoding,
                sep=None,  # Auto-detect separator
                engine='python'
            )
            
            total_rows = len(df)
            logger.info(f"Processing {total_rows} rows from AMDEC file")
            
            # Validate required columns
            required_columns = ['Désignation', 'Date intervention']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Get or create equipment
                    equipment = ImportService.get_or_create_equipment(
                        db,
                        str(row['Désignation']).strip()
                    )
                    
                    # Parse dates
                    date_intervention = ImportService.parse_french_date(
                        row.get('Date intervention')
                    )
                    date_demande = ImportService.parse_french_date(
                        row.get('Date demande'),
                        include_time=True
                    )
                    
                    if not date_intervention:
                        errors.append(f"Row {idx+2}: Invalid intervention date")
                        failed_rows += 1
                        continue
                    
                    # Clean numeric fields
                    duree_arret = ImportService.clean_numeric(
                        row.get('Durée arrêt (h)', 0)
                    )
                    cout_materiel = ImportService.clean_numeric(
                        row.get('Coût matériel', 0)
                    )
                    
                    # Create intervention
                    intervention = Intervention(
                        equipment_id=equipment.id,
                        type_panne=str(row.get('Type de panne', '')).strip() or None,
                        cause=str(row.get('Cause', '')).strip() or None,
                        organe=str(row.get('Organe', '')).strip() or None,
                        date_intervention=date_intervention,
                        date_demande=date_demande,
                        resume_intervention=str(row.get('Résumé intervention', '')).strip() or None,
                        duree_arret=duree_arret,
                        cout_materiel=cout_materiel,
                        cout_total=cout_materiel,  # Will be updated later
                        status=InterventionStatus.COMPLETED
                    )
                    
                    db.add(intervention)
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx+2}: {e}")
                    errors.append(f"Row {idx+2}: {str(e)}")
                    failed_rows += 1
                    continue
            
            # Commit all changes
            db.commit()
            
            # Create import log
            duration = (datetime.now() - start_time).total_seconds()
            import_log = ImportLog(
                filename=filename,
                import_type='amdec',
                status='success' if failed_rows == 0 else 'partial',
                total_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_messages='\n'.join(errors) if errors else None,
                user_id=user_id,
                duration_seconds=duration
            )
            db.add(import_log)
            db.commit()
            
            return {
                "status": "success" if failed_rows == 0 else "partial",
                "message": f"Imported {successful_rows}/{total_rows} interventions",
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "errors": errors[:10],  # Return first 10 errors
                "duration_seconds": duration,
                "import_log_id": import_log.id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"AMDEC import failed: {e}", exc_info=True)
            
            # Create failed import log
            duration = (datetime.now() - start_time).total_seconds()
            import_log = ImportLog(
                filename=filename,
                import_type='amdec',
                status='failed',
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                error_messages=str(e),
                user_id=user_id,
                duration_seconds=duration
            )
            db.add(import_log)
            db.commit()
            
            raise Exception(f"Import failed: {str(e)}")
    
    @staticmethod
    async def import_gmao_csv(
        db: Session,
        file_content: bytes,
        filename: str,
        user_id: str = "system"
    ) -> Dict:
        """
        Import GMAO CSV file with spare parts
        
        Expected columns:
        - Désignation
        - Type de panne
        - Durée arrêt (h)
        - Date intervention
        - Coût matériel
        - [Pièce].Désignation
        - [Pièce].Référence
        - [Pièce].Quantité
        
        Args:
            db: Database session
            file_content: File bytes
            filename: Original filename
            user_id: User performing import
        
        Returns:
            Dict with import statistics
        """
        start_time = datetime.now()
        errors = []
        successful_rows = 0
        failed_rows = 0
        
        try:
            # Detect encoding
            encoding = ImportService.detect_encoding(file_content)
            
            # Read CSV
            df = pd.read_csv(
                io.BytesIO(file_content),
                encoding=encoding,
                sep=None,
                engine='python'
            )
            
            total_rows = len(df)
            logger.info(f"Processing {total_rows} rows from GMAO file")
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Get or create equipment
                    equipment = ImportService.get_or_create_equipment(
                        db,
                        str(row['Désignation']).strip()
                    )
                    
                    # Parse date
                    date_intervention = ImportService.parse_french_date(
                        row.get('Date intervention')
                    )
                    
                    if not date_intervention:
                        errors.append(f"Row {idx+2}: Invalid intervention date")
                        failed_rows += 1
                        continue
                    
                    # Find or create intervention for this equipment and date
                    intervention = db.query(Intervention).filter(
                        Intervention.equipment_id == equipment.id,
                        Intervention.date_intervention == date_intervention
                    ).first()
                    
                    if not intervention:
                        duree_arret = ImportService.clean_numeric(
                            row.get('Durée arrêt (h)', 0)
                        )
                        cout_materiel = ImportService.clean_numeric(
                            row.get('Coût matériel', 0)
                        )
                        
                        intervention = Intervention(
                            equipment_id=equipment.id,
                            type_panne=str(row.get('Type de panne', '')).strip() or None,
                            date_intervention=date_intervention,
                            duree_arret=duree_arret,
                            cout_materiel=cout_materiel,
                            cout_total=cout_materiel,
                            status=InterventionStatus.COMPLETED
                        )
                        db.add(intervention)
                        db.flush()
                    
                    # Add spare part if specified
                    part_designation = row.get('[Pièce].Désignation')
                    part_reference = row.get('[Pièce].Référence')
                    
                    if not pd.isna(part_designation) and not pd.isna(part_reference):
                        # Get or create spare part
                        spare_part = ImportService.get_or_create_spare_part(
                            db,
                            str(part_designation).strip(),
                            str(part_reference).strip()
                        )
                        
                        # Parse quantity
                        quantite = ImportService.clean_numeric(
                            row.get('[Pièce].Quantité', 1)
                        )
                        
                        # Add to intervention
                        intervention_part = InterventionPart(
                            intervention_id=intervention.id,
                            spare_part_id=spare_part.id,
                            quantite=quantite,
                            cout_unitaire=spare_part.cout_unitaire,
                            cout_total=quantite * spare_part.cout_unitaire
                        )
                        db.add(intervention_part)
                    
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx+2}: {e}")
                    errors.append(f"Row {idx+2}: {str(e)}")
                    failed_rows += 1
                    continue
            
            db.commit()
            
            # Create import log
            duration = (datetime.now() - start_time).total_seconds()
            import_log = ImportLog(
                filename=filename,
                import_type='gmao',
                status='success' if failed_rows == 0 else 'partial',
                total_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_messages='\n'.join(errors) if errors else None,
                user_id=user_id,
                duration_seconds=duration
            )
            db.add(import_log)
            db.commit()
            
            return {
                "status": "success" if failed_rows == 0 else "partial",
                "message": f"Imported {successful_rows}/{total_rows} rows with spare parts",
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "errors": errors[:10],
                "duration_seconds": duration,
                "import_log_id": import_log.id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"GMAO import failed: {e}", exc_info=True)
            raise Exception(f"Import failed: {str(e)}")
    
    @staticmethod
    async def import_workload_csv(
        db: Session,
        file_content: bytes,
        filename: str,
        user_id: str = "system"
    ) -> Dict:
        """
        Import Workload CSV with technician assignments
        
        Expected columns:
        - Désignation
        - Type de panne
        - Date intervention
        - Nombre d'heures MO
        - Coût total intervention
        - [MO interne].Nom
        - [MO interne].Prénom
        - [MO interne].Nombre d'heures
        
        Args:
            db: Database session
            file_content: File bytes
            filename: Original filename
            user_id: User performing import
        
        Returns:
            Dict with import statistics
        """
        start_time = datetime.now()
        errors = []
        successful_rows = 0
        failed_rows = 0
        
        try:
            encoding = ImportService.detect_encoding(file_content)
            
            df = pd.read_csv(
                io.BytesIO(file_content),
                encoding=encoding,
                sep=None,
                engine='python'
            )
            
            total_rows = len(df)
            logger.info(f"Processing {total_rows} rows from Workload file")
            
            for idx, row in df.iterrows():
                try:
                    # Get equipment
                    equipment = ImportService.get_or_create_equipment(
                        db,
                        str(row['Désignation']).strip()
                    )
                    
                    # Parse date
                    date_intervention = ImportService.parse_french_date(
                        row.get('Date intervention')
                    )
                    
                    if not date_intervention:
                        errors.append(f"Row {idx+2}: Invalid intervention date")
                        failed_rows += 1
                        continue
                    
                    # Find or create intervention
                    intervention = db.query(Intervention).filter(
                        Intervention.equipment_id == equipment.id,
                        Intervention.date_intervention == date_intervention
                    ).first()
                    
                    if not intervention:
                        intervention = Intervention(
                            equipment_id=equipment.id,
                            type_panne=str(row.get('Type de panne', '')).strip() or None,
                            date_intervention=date_intervention,
                            status=InterventionStatus.COMPLETED
                        )
                        db.add(intervention)
                        db.flush()
                    
                    # Update costs and hours
                    nombre_heures_mo = ImportService.clean_numeric(
                        row.get('Nombre d\'heures MO', 0)
                    )
                    cout_total = ImportService.clean_numeric(
                        row.get('Coût total intervention', 0)
                    )
                    
                    intervention.nombre_heures_mo = nombre_heures_mo
                    intervention.cout_total = cout_total
                    intervention.cout_main_oeuvre = cout_total - intervention.cout_materiel
                    
                    # Add technician assignment
                    nom = row.get('[MO interne].Nom')
                    prenom = row.get('[MO interne].Prénom')
                    
                    if not pd.isna(nom) and not pd.isna(prenom):
                        technician = ImportService.get_or_create_technician(
                            db,
                            str(nom).strip(),
                            str(prenom).strip()
                        )
                        
                        heures_tech = ImportService.clean_numeric(
                            row.get('[MO interne].Nombre d\'heures', 0)
                        )
                        
                        assignment = TechnicianAssignment(
                            intervention_id=intervention.id,
                            technician_id=technician.id,
                            nombre_heures=heures_tech,
                            taux_horaire=technician.taux_horaire,
                            cout_main_oeuvre=heures_tech * technician.taux_horaire
                        )
                        db.add(assignment)
                    
                    successful_rows += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx+2}: {e}")
                    errors.append(f"Row {idx+2}: {str(e)}")
                    failed_rows += 1
                    continue
            
            db.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            import_log = ImportLog(
                filename=filename,
                import_type='workload',
                status='success' if failed_rows == 0 else 'partial',
                total_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_messages='\n'.join(errors) if errors else None,
                user_id=user_id,
                duration_seconds=duration
            )
            db.add(import_log)
            db.commit()
            
            return {
                "status": "success" if failed_rows == 0 else "partial",
                "message": f"Imported {successful_rows}/{total_rows} workload entries",
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "errors": errors[:10],
                "duration_seconds": duration,
                "import_log_id": import_log.id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Workload import failed: {e}", exc_info=True)
            raise Exception(f"Import failed: {str(e)}")