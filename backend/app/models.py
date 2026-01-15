"""
SQLAlchemy ORM models for GMAO (Maintenance Management) system.
Defines database schema with relationships and constraints.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, Date, DateTime,
    ForeignKey, Enum as SQLEnum, Index, Boolean, LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from datetime import date
from app.database import Base
from sqlalchemy.dialects.postgresql import JSON


# ==================== USER ROLES ====================
# Roles are read from Supabase app_metadata.role (single source of truth)
# This enum is used for validation and role guards in the API

class UserRole(str, enum.Enum):
    """User roles for RBAC. Stored in Supabase app_metadata."""
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


# ==================== STATUS ENUMS ====================
class EquipmentStatus(str, enum.Enum):
    """Equipment operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class InterventionStatus(str, enum.Enum):
    """Intervention workflow status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TechnicianStatus(str, enum.Enum):
    """Technician employment status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"


class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


# ==================== CORE MODELS ====================

class Equipment(Base):
    """
    Equipment/Machine model representing physical assets.
    Central entity linked to all maintenance interventions.
    """
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    designation = Column(String(200), unique=True, nullable=False, index=True)
    type = Column(String(100))  # Machine type/category
    location = Column(String(200))  # Physical location
    status = Column(
        SQLEnum(EquipmentStatus),
        default=EquipmentStatus.ACTIVE,
        nullable=False
    )
    acquisition_date = Column(Date)
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100), unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    interventions = relationship("Intervention", back_populates="equipment", cascade="all, delete-orphan")
    failure_modes = relationship("FailureMode", back_populates="equipment", cascade="all, delete-orphan")
    required_skills = relationship("EquipmentRequiredSkill", back_populates="equipment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Equipment(id={self.id}, designation='{self.designation}', status='{self.status}')>"


class Intervention(Base):
    """
    Maintenance intervention/work order model.
    Tracks all maintenance activities with costs, downtime, and outcomes.
    """
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    
    # Failure/Issue details
    type_panne = Column(String(100), index=True)  # Failure type (Hydraulique, Mécanique, etc.)
    categorie_panne = Column(String(100))  # Failure category
    cause = Column(Text)  # Root cause analysis
    organe = Column(String(200))  # Affected component/subassembly
    
    # Dates
    date_demande = Column(DateTime, index=True)  # Request datetime
    date_intervention = Column(Date, nullable=False, index=True)  # Intervention date
    
    # Intervention details
    resume_intervention = Column(Text)  # Detailed description of work performed
    resultat = Column(Text)  # Outcome/result
    duree_arret = Column(Float, default=0.0)  # Downtime in hours
    
    # Costs
    cout_materiel = Column(Float, default=0.0)  # Material cost
    cout_main_oeuvre = Column(Float, default=0.0)  # Labor cost (calculated)
    cout_total = Column(Float, default=0.0)  # Total cost
    
    # Workload
    nombre_heures_mo = Column(Float, default=0.0)  # Total labor hours
    
    # Status
    status = Column(
        SQLEnum(InterventionStatus),
        default=InterventionStatus.OPEN,
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    equipment = relationship("Equipment", back_populates="interventions")
    parts = relationship("InterventionPart", back_populates="intervention", cascade="all, delete-orphan")
    technician_assignments = relationship("TechnicianAssignment", back_populates="intervention", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_intervention_date_type', 'date_intervention', 'type_panne'),
        Index('idx_intervention_equipment_date', 'equipment_id', 'date_intervention'),
    )

    def __repr__(self):
        return f"<Intervention(id={self.id}, equipment_id={self.equipment_id}, type='{self.type_panne}', date='{self.date_intervention}')>"


class SparePart(Base):
    """
    Spare parts inventory model.
    Tracks parts used in maintenance with stock levels.
    """
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    designation = Column(String(200), nullable=False)  # Part name
    reference = Column(String(100), unique=True, nullable=False, index=True)  # Part number
    description = Column(Text)
    
    # Pricing and stock
    cout_unitaire = Column(Float, default=0.0)  # Unit cost
    stock_actuel = Column(Integer, default=0)  # Current stock level
    seuil_alerte = Column(Integer, default=10)  # Alert threshold
    unite = Column(String(20), default="pcs")  # Unit of measure
    
    # Supplier info
    fournisseur = Column(String(200))  # Supplier name
    delai_livraison = Column(Integer)  # Delivery time in days
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    intervention_usages = relationship("InterventionPart", back_populates="spare_part")

    def __repr__(self):
        return f"<SparePart(id={self.id}, ref='{self.reference}', designation='{self.designation}', stock={self.stock_actuel})>"


class Technician(Base):
    """
    Technician/maintenance personnel model.
    Tracks internal workforce with skills and rates.
    """
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)  # Last name
    prenom = Column(String(100), nullable=False)  # First name
    email = Column(String(200), unique=True, nullable=False, index=True)
    telephone = Column(String(20))
    
    # Work details
    specialite = Column(String(100))  # Specialty (Hydraulique, Électrique, etc.)
    taux_horaire = Column(Float, default=0.0)  # Hourly rate
    niveau_competence = Column(String(50))  # Skill level
    
    # Status
    status = Column(
        SQLEnum(TechnicianStatus),
        default=TechnicianStatus.ACTIVE,
        nullable=False
    )
    
    # Employment
    date_embauche = Column(Date)  # Hire date
    matricule = Column(String(50), unique=True)  # Employee ID
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    assignments = relationship("TechnicianAssignment", back_populates="technician")
    acquired_skills = relationship("TechnicianSkill", back_populates="technician", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Technician(id={self.id}, name='{self.prenom} {self.nom}', specialite='{self.specialite}')>"


# ==================== ASSOCIATION MODELS ====================

class InterventionPart(Base):
    """
    Many-to-many association between interventions and spare parts.
    Tracks parts consumed in each intervention with quantities and costs.
    """
    __tablename__ = "intervention_parts"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id"), nullable=False, index=True)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id"), nullable=False, index=True)
    
    quantite = Column(Float, nullable=False, default=1.0)  # Quantity used
    cout_unitaire = Column(Float, default=0.0)  # Unit cost at time of use
    cout_total = Column(Float, default=0.0)  # Total cost for this part usage
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    intervention = relationship("Intervention", back_populates="parts")
    spare_part = relationship("SparePart", back_populates="intervention_usages")

    __table_args__ = (
        Index('idx_intervention_parts', 'intervention_id', 'spare_part_id'),
    )

    def __repr__(self):
        return f"<InterventionPart(intervention_id={self.intervention_id}, part_id={self.spare_part_id}, qty={self.quantite})>"


class TechnicianAssignment(Base):
    """
    Many-to-many association between interventions and technicians.
    Tracks technician work hours and labor costs per intervention.
    """
    __tablename__ = "technician_assignments"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id"), nullable=False, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    
    nombre_heures = Column(Float, nullable=False, default=0.0)  # Hours worked
    taux_horaire = Column(Float, default=0.0)  # Hourly rate at time of work
    cout_main_oeuvre = Column(Float, default=0.0)  # Labor cost for this assignment
    
    # Work period
    date_debut = Column(DateTime)  # Start datetime
    date_fin = Column(DateTime)  # End datetime
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    intervention = relationship("Intervention", back_populates="technician_assignments")
    technician = relationship("Technician", back_populates="assignments")

    __table_args__ = (
        Index('idx_technician_assignments', 'intervention_id', 'technician_id'),
    )

    def __repr__(self):
        return f"<TechnicianAssignment(intervention_id={self.intervention_id}, technician_id={self.technician_id}, hours={self.nombre_heures})>"


# ==================== AUDIT/LOGGING MODEL ====================

class ImportLog(Base):
    """
    Import history and audit log for CSV imports.
    Tracks successful and failed imports with detailed messages.
    """
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(200), nullable=False)
    import_type = Column(String(50), nullable=False, index=True)  # amdec, gmao, workload
    status = Column(String(20), nullable=False)  # success, failed, partial
    
    # Statistics
    total_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Details
    error_messages = Column(Text)  # JSON or text with error details
    user_id = Column(String(100))  # Who performed the import
    duration_seconds = Column(Float)  # Import duration
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<ImportLog(id={self.id}, type='{self.import_type}', status='{self.status}', rows={self.successful_rows}/{self.total_rows})>"


# ==================== RAG MODELS ====================

class RAGDocument(Base):
    """
    RAG document model for tracking uploaded documents.
    Stores metadata and processing status for vector indexing.
    """
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    mime_type = Column(String(100))
    
    # Processing status
    status = Column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Indexing metadata
    chunk_count = Column(Integer, default=0)  # Number of text chunks
    index_name = Column(String(200), index=True)  # FAISS index identifier
    embedding_model = Column(String(100))  # Model used for embeddings
    
    # Content metadata
    document_hash = Column(String(64), unique=True, index=True)  # SHA-256 hash
    total_tokens = Column(Integer, default=0)  # Approximate token count
    
    # Processing details
    processing_time_seconds = Column(Float)
    error_message = Column(Text)
    
    # User tracking
    uploaded_by = Column(String(100))  # User identifier
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    indexed_at = Column(DateTime)  # When successfully indexed

    # Relationships
    chunks = relationship("RAGDocumentChunk", back_populates="document", cascade="all, delete-orphan")
    queries = relationship("RAGQuery", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_rag_doc_status_created', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<RAGDocument(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class RAGDocumentChunk(Base):
    """
    Individual text chunks from documents for vector search.
    Stores text segments with metadata for retrieval.
    """
    __tablename__ = "rag_document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("rag_documents.id"), nullable=False, index=True)
    
    # Chunk content
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    chunk_hash = Column(String(64), index=True)  # Hash for deduplication
    
    # Metadata
    page_number = Column(Integer)  # For PDFs
    section_title = Column(String(500))
    token_count = Column(Integer, default=0)
    
    # Vector metadata
    vector_id = Column(String(200))  # Reference to FAISS vector
    embedding_cached = Column(Boolean, default=False)  # Redis cache status
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    document = relationship("RAGDocument", back_populates="chunks")

    __table_args__ = (
        Index('idx_rag_chunk_doc_index', 'document_id', 'chunk_index'),
    )

    def __repr__(self):
        return f"<RAGDocumentChunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"


class RAGQuery(Base):
    """
    Query history and analytics for RAG system.
    Tracks user queries, responses, and performance metrics.
    """
    __tablename__ = "rag_queries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), index=True)  # For caching
    
    # Response
    response_text = Column(Text)
    response_sources = Column(JSON)  # List of source chunks used
    
    # Performance metrics
    retrieval_time_ms = Column(Float)  # Time to retrieve relevant chunks
    generation_time_ms = Column(Float)  # Time to generate response
    total_time_ms = Column(Float)  # Total query time
    
    # Retrieval metadata
    chunks_retrieved = Column(Integer, default=0)
    top_k = Column(Integer, default=5)  # Number of chunks requested
    similarity_threshold = Column(Float)
    
    # Response quality
    confidence_score = Column(Float)  # LLM confidence (if available)
    user_feedback = Column(String(20))  # positive, negative, neutral
    feedback_comment = Column(Text)
    
    # Related document
    document_id = Column(Integer, ForeignKey("rag_documents.id"), index=True)
    
    # Cache info
    cache_hit = Column(Boolean, default=False)
    cache_key = Column(String(200))
    
    # User tracking
    user_id = Column(String(100))
    session_id = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    document = relationship("RAGDocument", back_populates="queries")

    __table_args__ = (
        Index('idx_rag_query_created', 'created_at'),
        Index('idx_rag_query_cache', 'query_hash', 'cache_hit'),
    )

    def __repr__(self):
        return f"<RAGQuery(id={self.id}, query='{self.query_text[:50]}...', cache_hit={self.cache_hit})>"


class RAGIndexMetadata(Base):
    """
    Metadata for FAISS vector indexes.
    Tracks index versions, statistics, and rebuild history.
    """
    __tablename__ = "rag_index_metadata"

    id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String(200), unique=True, nullable=False, index=True)
    
    # Index details
    index_type = Column(String(50), default="faiss")  # faiss, annoy, etc.
    dimension = Column(Integer, nullable=False)  # Vector dimension
    total_vectors = Column(Integer, default=0)
    
    # Configuration
    embedding_model = Column(String(100), nullable=False)
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)
    
    # Performance
    build_time_seconds = Column(Float)
    index_size_bytes = Column(Integer)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_rebuild_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<RAGIndexMetadata(name='{self.index_name}', vectors={self.total_vectors}, active={self.is_active})>"
    

# ==================== AMDEC MODELS ====================

class FailureMode(Base):
    """
    Failure Mode model for AMDEC analysis.
    Represents potential failure modes for equipment with their effects and causes.
    """
    __tablename__ = "failure_modes"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    
    # Failure mode details
    mode_name = Column(String(200), nullable=False)  # Nom du mode de défaillance
    description = Column(Text)  # Description détaillée
    failure_cause = Column(Text)  # Cause de la défaillance
    failure_effect = Column(Text)  # Effet de la défaillance
    
    # Detection method
    detection_method = Column(String(200))  # Méthode de détection
    prevention_action = Column(Text)  # Action préventive recommandée
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    equipment = relationship("Equipment", back_populates="failure_modes")
    rpn_analyses = relationship("RPNAnalysis", back_populates="failure_mode", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_failure_mode_equipment', 'equipment_id', 'is_active'),
    )

    def __repr__(self):
        return f"<FailureMode(id={self.id}, equipment_id={self.equipment_id}, mode='{self.mode_name}')>"


class RPNAnalysis(Base):
    """
    RPN (Risk Priority Number) Analysis model.
    Stores G (Gravité/Severity), O (Occurrence), D (Détection) scores and calculates RPN.
    """
    __tablename__ = "rpn_analyses"

    id = Column(Integer, primary_key=True, index=True)
    failure_mode_id = Column(Integer, ForeignKey("failure_modes.id"), nullable=False, index=True)
    
    # RPN Components (Scale 1-10)
    gravity = Column(Integer, nullable=False)  # G - Gravité/Severity
    occurrence = Column(Integer, nullable=False)  # O - Occurrence/Frequency
    detection = Column(Integer, nullable=False)  # D - Détection/Detection difficulty
    
    # Calculated RPN (G x O x D)
    rpn_value = Column(Integer, nullable=False, index=True)  # RPN = G × O × D
    
    # Analysis context
    analysis_date = Column(Date, nullable=False, default=date.today, index=True)
    analyst_name = Column(String(100))  # Person who performed analysis
    comments = Column(Text)  # Additional notes
    
    # Action tracking
    corrective_action = Column(Text)  # Action corrective proposée
    action_status = Column(String(50), default="pending")  # pending, in_progress, completed
    action_due_date = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    failure_mode = relationship("FailureMode", back_populates="rpn_analyses")

    __table_args__ = (
        Index('idx_rpn_value_date', 'rpn_value', 'analysis_date'),
        Index('idx_rpn_failure_mode_date', 'failure_mode_id', 'analysis_date'),
    )

    def __repr__(self):
        return f"<RPNAnalysis(id={self.id}, failure_mode_id={self.failure_mode_id}, RPN={self.rpn_value})>"


class Skill(Base):
    """
    Skills/Competencies model.
    Represents technical skills required for equipment maintenance.
    """
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    
    # Skill details
    skill_name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100))  # e.g., Hydraulique, Électrique, Mécanique
    
    # Skill level
    difficulty_level = Column(Integer, default=1)  # 1-5 scale
    certification_required = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    technician_skills = relationship("TechnicianSkill", back_populates="skill", cascade="all, delete-orphan")
    equipment_skills = relationship("EquipmentRequiredSkill", back_populates="skill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.skill_name}', category='{self.category}')>"


class TechnicianSkill(Base):
    """
    Many-to-many association between technicians and skills.
    Tracks which skills each technician has acquired with proficiency level.
    """
    __tablename__ = "technician_skills"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    
    # Proficiency
    proficiency_level = Column(Integer, nullable=False, default=1)  # 1-5 scale
    acquisition_date = Column(Date)  # Date when skill was acquired
    certification_date = Column(Date)  # Date of certification (if applicable)
    certification_expiry = Column(Date)  # Expiry date for certifications
    
    # Validation
    is_validated = Column(Boolean, default=False)  # Validated by supervisor
    validated_by = Column(String(100))  # Who validated the skill
    validated_at = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    technician = relationship("Technician", back_populates="acquired_skills")
    skill = relationship("Skill", back_populates="technician_skills")

    __table_args__ = (
        Index('idx_technician_skills', 'technician_id', 'skill_id'),
    )

    def __repr__(self):
        return f"<TechnicianSkill(technician_id={self.technician_id}, skill_id={self.skill_id}, level={self.proficiency_level})>"


class EquipmentRequiredSkill(Base):
    """
    Many-to-many association between equipment and required skills.
    Defines which skills are needed to maintain specific equipment.
    """
    __tablename__ = "equipment_required_skills"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    
    # Requirement details
    required_proficiency_level = Column(Integer, nullable=False, default=3)  # Minimum level needed
    is_mandatory = Column(Boolean, default=True)  # Must-have vs nice-to-have
    priority = Column(Integer, default=1)  # Priority ranking for this skill
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    equipment = relationship("Equipment", back_populates="required_skills")
    skill = relationship("Skill", back_populates="equipment_skills")

    __table_args__ = (
        Index('idx_equipment_skills', 'equipment_id', 'skill_id'),
    )

    def __repr__(self):
        return f"<EquipmentRequiredSkill(equipment_id={self.equipment_id}, skill_id={self.skill_id}, level={self.required_proficiency_level})>"


class OcrExtraction(Base):
    """
    Model for storing OCR extractions permanently.
    """
    __tablename__ = "ocr_extractions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    format = Column(String(20), nullable=False)  # markdown, html, json
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OcrExtraction(id={self.id}, filename='{self.filename}', format='{self.format}')>"


class KnowledgeBaseDocument(Base):
    """
    Knowledge Base document representing maintenance, safety, and training manuals.
    Indexed for RAG retrieval.
    """
    __tablename__ = "knowledge_base_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False) # Formation, Safety, Enterprise, AMDEC
    type_panne = Column(String(100), nullable=True) # Optional link to failure type
    content = Column(Text, nullable=False) # Markdown content
    safety_level = Column(String(50), default="Low") # High, Medium, Low
    
    version = Column(Integer, default=1)
    indexed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<KnowledgeBaseDocument(id={self.id}, title='{self.title}', version={self.version})>"
