"""
Pydantic schemas for request/response validation and serialization.
Provides data validation, type checking, and API documentation.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


# ==================== ENUMS ====================

class EquipmentStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class InterventionStatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TechnicianStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"


class DocumentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


# ==================== EQUIPMENT SCHEMAS ====================

class EquipmentBase(BaseModel):
    designation: str = Field(..., min_length=1, max_length=200)
    type: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    status: EquipmentStatusEnum = EquipmentStatusEnum.ACTIVE
    acquisition_date: Optional[date] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    designation: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    status: Optional[EquipmentStatusEnum] = None
    acquisition_date: Optional[date] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)


class EquipmentResponse(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EquipmentWithStats(EquipmentResponse):
    """Equipment response with aggregated statistics"""
    total_interventions: int = 0
    total_downtime_hours: float = 0.0
    total_cost: float = 0.0
    mtbf: Optional[float] = None
    mttr: Optional[float] = None
    availability: Optional[float] = None


# ==================== INTERVENTION SCHEMAS ====================

class InterventionBase(BaseModel):
    equipment_id: int
    type_panne: Optional[str] = Field(None, max_length=100)
    categorie_panne: Optional[str] = Field(None, max_length=100)
    cause: Optional[str] = None
    organe: Optional[str] = Field(None, max_length=200)
    date_demande: Optional[datetime] = None
    date_intervention: date
    resume_intervention: Optional[str] = None
    resultat: Optional[str] = None
    duree_arret: float = Field(0.0, ge=0)
    cout_materiel: float = Field(0.0, ge=0)
    cout_main_oeuvre: float = 0.0
    cout_total: float = 0.0
    nombre_heures_mo: float = Field(0.0, ge=0)
    status: InterventionStatusEnum = InterventionStatusEnum.OPEN

    @field_validator('date_intervention')
    @classmethod
    def validate_intervention_date(cls, v):
        if v > date.today():
            raise ValueError('Intervention date cannot be in the future')
        return v

    @field_validator('date_demande')
    @classmethod
    def validate_request_date(cls, v, info):
        if v and 'date_intervention' in info.data:
            if v.date() > info.data['date_intervention']:
                raise ValueError('Request date must be before or equal to intervention date')
        return v


class InterventionCreate(InterventionBase):
    pass


class InterventionUpdate(BaseModel):
    equipment_id: Optional[int] = None
    type_panne: Optional[str] = Field(None, max_length=100)
    categorie_panne: Optional[str] = Field(None, max_length=100)
    cause: Optional[str] = None
    organe: Optional[str] = Field(None, max_length=200)
    date_demande: Optional[datetime] = None
    date_intervention: Optional[date] = None
    resume_intervention: Optional[str] = None
    resultat: Optional[str] = None
    duree_arret: Optional[float] = Field(None, ge=0)
    cout_materiel: Optional[float] = Field(None, ge=0)
    cout_main_oeuvre: Optional[float] = None
    cout_total: Optional[float] = None
    nombre_heures_mo: Optional[float] = Field(None, ge=0)
    status: Optional[InterventionStatusEnum] = None


class InterventionResponse(InterventionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InterventionWithDetails(InterventionResponse):
    """Intervention response with equipment name and related data"""
    equipment_designation: Optional[str] = None
    parts_count: int = 0
    technicians_count: int = 0


# ==================== SPARE PART SCHEMAS ====================

class SparePartBase(BaseModel):
    designation: str = Field(..., min_length=1, max_length=200)
    reference: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    cout_unitaire: float = Field(0.0, ge=0)
    stock_actuel: int = Field(0, ge=0)
    seuil_alerte: int = Field(10, gt=0)
    unite: str = Field("pcs", max_length=20)
    fournisseur: Optional[str] = Field(None, max_length=200)
    delai_livraison: Optional[int] = Field(None, ge=0)


class SparePartCreate(SparePartBase):
    pass


class SparePartUpdate(BaseModel):
    designation: Optional[str] = Field(None, min_length=1, max_length=200)
    reference: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    cout_unitaire: Optional[float] = Field(None, ge=0)
    stock_actuel: Optional[int] = Field(None, ge=0)
    seuil_alerte: Optional[int] = Field(None, gt=0)
    unite: Optional[str] = Field(None, max_length=20)
    fournisseur: Optional[str] = Field(None, max_length=200)
    delai_livraison: Optional[int] = Field(None, ge=0)


class SparePartResponse(SparePartBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool = False

    class Config:
        from_attributes = True


# ==================== TECHNICIAN SCHEMAS ====================

class TechnicianBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telephone: Optional[str] = Field(None, max_length=20)
    specialite: Optional[str] = Field(None, max_length=100)
    taux_horaire: float = Field(0.0, ge=0)
    niveau_competence: Optional[str] = Field(None, max_length=50)
    status: TechnicianStatusEnum = TechnicianStatusEnum.ACTIVE
    date_embauche: Optional[date] = None
    matricule: Optional[str] = Field(None, max_length=50)


class TechnicianCreate(TechnicianBase):
    pass


class TechnicianUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(None, max_length=20)
    specialite: Optional[str] = Field(None, max_length=100)
    taux_horaire: Optional[float] = Field(None, gt=0)
    niveau_competence: Optional[str] = Field(None, max_length=50)
    status: Optional[TechnicianStatusEnum] = None
    date_embauche: Optional[date] = None
    matricule: Optional[str] = Field(None, max_length=50)


class TechnicianResponse(TechnicianBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TechnicianWithStats(TechnicianResponse):
    """Technician response with workload statistics"""
    total_interventions: int = 0
    total_hours: float = 0.0
    total_labor_cost: float = 0.0


# ==================== ASSOCIATION SCHEMAS ====================

class InterventionPartBase(BaseModel):
    spare_part_id: int
    quantite: float = Field(..., gt=0)
    cout_unitaire: float = Field(0.0, ge=0)
    cout_total: float = Field(0.0, ge=0)


class InterventionPartCreate(BaseModel):
    spare_part_id: int
    quantite: float = Field(..., gt=0)


class InterventionPartResponse(InterventionPartBase):
    id: int
    intervention_id: int
    spare_part_designation: Optional[str] = None
    spare_part_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TechnicianAssignmentBase(BaseModel):
    technician_id: int
    nombre_heures: float = Field(..., gt=0)
    taux_horaire: float = Field(0.0, ge=0)
    cout_main_oeuvre: float = Field(0.0, ge=0)
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class TechnicianAssignmentCreate(BaseModel):
    technician_id: int
    nombre_heures: float = Field(..., gt=0)
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class TechnicianAssignmentResponse(TechnicianAssignmentBase):
    id: int
    intervention_id: int
    technician_nom: Optional[str] = None
    technician_prenom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== KPI SCHEMAS ====================

class MTBFResponse(BaseModel):
    """Mean Time Between Failures response"""
    mtbf_hours: float
    total_operating_hours: float
    failure_count: int
    equipment_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class MTTRResponse(BaseModel):
    """Mean Time To Repair response"""
    mttr_hours: float
    total_downtime_hours: float
    intervention_count: int
    equipment_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class AvailabilityResponse(BaseModel):
    """Equipment Availability response"""
    availability_percentage: float
    total_hours: float
    downtime_hours: float
    uptime_hours: float
    equipment_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class FailureDistribution(BaseModel):
    """Failure type distribution"""
    type_panne: str
    count: int
    percentage: float
    total_downtime: float
    average_downtime: float


class CostBreakdown(BaseModel):
    """Cost analysis breakdown"""
    total_cost: float
    material_cost: float
    labor_cost: float
    material_percentage: float
    labor_percentage: float
    intervention_count: int


class DashboardKPIs(BaseModel):
    """Comprehensive dashboard KPIs"""
    mtbf: Optional[MTBFResponse] = None
    mttr: Optional[MTTRResponse] = None
    availability: Optional[AvailabilityResponse] = None
    cost_breakdown: Optional[CostBreakdown] = None
    failure_distribution: List[FailureDistribution] = []
    total_interventions: int = 0
    open_interventions: int = 0
    equipment_count: int = 0
    technician_count: int = 0


# ==================== IMPORT/EXPORT SCHEMAS ====================

class ImportResponse(BaseModel):
    """Import operation response"""
    status: str
    message: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: List[str] = []
    duration_seconds: float
    import_log_id: Optional[int] = None


class ImportLogResponse(BaseModel):
    """Import log entry"""
    id: int
    filename: str
    import_type: str
    status: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_messages: Optional[str] = None
    user_id: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== RAG SCHEMAS ====================

class DocumentSource(BaseModel):
    """Source document information for RAG responses"""
    document_id: int
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    relevance_score: float
    excerpt: str


class RAGQueryRequest(BaseModel):
    """Request schema for RAG queries"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query text")
    top_k: int = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    document_ids: Optional[List[int]] = Field(None, description="Filter by specific document IDs")
    use_cache: bool = Field(True, description="Use cached results if available")
    include_sources: bool = Field(True, description="Include source documents in response")


class RAGQueryResponse(BaseModel):
    """Response schema for RAG queries"""
    query: str
    response: str
    sources: List[DocumentSource] = []
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    chunks_retrieved: int
    cache_hit: bool = False
    confidence_score: Optional[float] = None


class RAGDocumentUploadResponse(BaseModel):
    """Response after uploading a document"""
    document_id: int
    filename: str
    file_size: int
    file_type: str
    status: DocumentStatusEnum
    message: str


class RAGDocumentResponse(BaseModel):
    """RAG document details"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: DocumentStatusEnum
    chunk_count: int
    total_tokens: int
    embedding_model: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RAGDocumentListResponse(BaseModel):
    """List of RAG documents with pagination"""
    total: int
    documents: List[RAGDocumentResponse]
    skip: int
    limit: int


class RAGIndexStatsResponse(BaseModel):
    """Statistics about the RAG vector index"""
    index_name: str
    total_documents: int
    total_chunks: int
    total_vectors: int
    embedding_model: str
    dimension: int
    index_size_mb: float
    last_updated: Optional[datetime] = None
    is_active: bool


class RAGReindexRequest(BaseModel):
    """Request to reindex documents"""
    document_ids: Optional[List[int]] = Field(None, description="Specific documents to reindex, or all if None")
    force: bool = Field(False, description="Force reindexing even if already indexed")
    clear_cache: bool = Field(True, description="Clear Redis cache after reindexing")


class RAGReindexResponse(BaseModel):
    """Response after reindexing"""
    status: str
    documents_processed: int
    chunks_created: int
    vectors_indexed: int
    duration_seconds: float
    errors: List[str] = []


class RAGCacheClearResponse(BaseModel):
    """Response after clearing cache"""
    status: str
    keys_deleted: int
    cache_type: str  # embeddings, queries, or all


class RAGHealthResponse(BaseModel):
    """Health check response for RAG system"""
    status: str
    ollama_available: bool
    redis_available: bool
    faiss_available: bool
    index_loaded: bool
    total_documents: int
    total_vectors: int
    last_query_time: Optional[datetime] = None


# ==================== RAG V2 SCHEMAS (Enhanced) ====================

class RAGCitationV2(BaseModel):
    """Structured citation with section info"""
    document_name: str
    document_id: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: str
    relevance_score: float
    formatted: str  # Human-readable citation string
    
    # Compatibility fields for frontend
    text: Optional[str] = None  # Alias for excerpt
    score: Optional[float] = None  # Alias for relevance_score
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Provide metadata dict for frontend compatibility"""
        return {
            "filename": self.document_name,
            "page_number": self.page_number,
            "section_title": self.section_title
        }


class RAGRoutingInfo(BaseModel):
    """Query routing decision details"""
    request_id: str
    primary_handler: str  # "sql", "document", "graph", "hybrid"
    handlers_used: List[str]
    intent: str  # "sql_analytics", "document", "graph", "hybrid"
    confidence: float
    reasoning: str
    kpi_detected: Optional[str] = None
    equipment_mentioned: List[str] = []


class RAGGraphContext(BaseModel):
    """Graph-derived context for the response"""
    related_equipment: List[str] = []
    failure_chains: List[Dict[str, Any]] = []
    causal_chains: List[Dict[str, Any]] = []
    summary: str = ""


class RAGQueryRequestV2(BaseModel):
    """Enhanced V2 request schema for RAG queries"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query text")
    top_k: int = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    similarity_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    document_ids: Optional[List[int]] = Field(None, description="Filter by specific document IDs")
    use_cache: bool = Field(True, description="Use cached results if available")
    include_sources: bool = Field(True, description="Include source documents in response")
    include_routing: bool = Field(True, description="Include routing decision details")
    include_graph_context: bool = Field(True, description="Include graph-derived context")
    use_hierarchical: bool = Field(True, description="Use hierarchical (section→chunk) retrieval")


class RAGQueryResponseV2(BaseModel):
    """Enhanced V2 response schema with routing, citations, and graph context"""
    query: str
    response: str
    
    # Enhanced citations
    citations: List[RAGCitationV2] = []
    
    # Routing info
    routing: Optional[RAGRoutingInfo] = None
    
    # Graph context
    graph_context: Optional[RAGGraphContext] = None
    
    # KPI data if SQL path was used
    kpi_data: Optional[Dict[str, Any]] = None
    
    # Timing
    routing_time_ms: float = 0.0
    retrieval_time_ms: float = 0.0
    graph_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Stats
    chunks_retrieved: int = 0
    cache_hit: bool = False
    provider_used: str = ""
    



# ==================== PAGINATION ====================

class PaginationParams(BaseModel):
    """Query parameters for pagination"""
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    total: int
    skip: int
    limit: int
    items: List

# =========== testing the llm ================

class SimpleChatRequest(BaseModel):
    prompt: str

class SimpleChatResponse(BaseModel):
    response: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


# ==================== FAILURE MODE SCHEMAS ====================

class FailureModeBase(BaseModel):
    equipment_id: int
    mode_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    failure_cause: Optional[str] = None
    failure_effect: Optional[str] = None
    detection_method: Optional[str] = Field(None, max_length=200)
    prevention_action: Optional[str] = None
    is_active: bool = True


class FailureModeCreate(FailureModeBase):
    pass


class FailureModeUpdate(BaseModel):
    mode_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    failure_cause: Optional[str] = None
    failure_effect: Optional[str] = None
    detection_method: Optional[str] = Field(None, max_length=200)
    prevention_action: Optional[str] = None
    is_active: Optional[bool] = None


class FailureModeResponse(FailureModeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FailureModeWithLatestRPN(FailureModeResponse):
    """Failure mode with its latest RPN analysis"""
    latest_rpn: Optional[int] = None
    latest_rpn_date: Optional[date] = None
    gravity: Optional[int] = None
    occurrence: Optional[int] = None
    detection: Optional[int] = None


# ==================== RPN ANALYSIS SCHEMAS ====================

class RPNAnalysisBase(BaseModel):
    failure_mode_id: int
    gravity: int = Field(..., ge=1, le=10, description="Gravité (1-10)")
    occurrence: int = Field(..., ge=1, le=10, description="Occurrence (1-10)")
    detection: int = Field(..., ge=1, le=10, description="Détection (1-10)")
    analysis_date: date = Field(default_factory=date.today)
    analyst_name: Optional[str] = Field(None, max_length=100)
    comments: Optional[str] = None
    corrective_action: Optional[str] = None
    action_status: str = Field("pending", pattern="^(pending|in_progress|completed)$")
    action_due_date: Optional[date] = None

    @field_validator('action_due_date')
    @classmethod
    def validate_due_date(cls, v, info):
        if v and 'analysis_date' in info.data:
            if v < info.data['analysis_date']:
                raise ValueError('Due date cannot be before analysis date')
        return v


class RPNAnalysisCreate(BaseModel):
    """Simplified creation schema - RPN is calculated automatically"""
    failure_mode_id: int
    gravity: int = Field(..., ge=1, le=10, description="Gravité (1-10)")
    occurrence: int = Field(..., ge=1, le=10, description="Occurrence (1-10)")
    detection: int = Field(..., ge=1, le=10, description="Détection (1-10)")
    analyst_name: Optional[str] = Field(None, max_length=100)
    comments: Optional[str] = None
    corrective_action: Optional[str] = None
    action_due_date: Optional[date] = None


class RPNAnalysisUpdate(BaseModel):
    gravity: Optional[int] = Field(None, ge=1, le=10)
    occurrence: Optional[int] = Field(None, ge=1, le=10)
    detection: Optional[int] = Field(None, ge=1, le=10)
    analyst_name: Optional[str] = Field(None, max_length=100)
    comments: Optional[str] = None
    corrective_action: Optional[str] = None
    action_status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed)$")
    action_due_date: Optional[date] = None


class RPNAnalysisResponse(RPNAnalysisBase):
    id: int
    rpn_value: int  # Calculated G x O x D
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RPNAnalysisWithDetails(RPNAnalysisResponse):
    """RPN Analysis with failure mode and equipment details"""
    failure_mode_name: Optional[str] = None
    equipment_id: Optional[int] = None
    equipment_designation: Optional[str] = None


# ==================== RPN RANKING SCHEMAS ====================

class RPNRankingItem(BaseModel):
    """Item in RPN ranking list"""
    failure_mode_id: int
    failure_mode_name: str
    equipment_id: int
    equipment_designation: str
    rpn_value: int
    gravity: int
    occurrence: int
    detection: int
    analysis_date: date
    corrective_action: Optional[str] = None
    action_status: str
    risk_level: str  # "critical", "high", "medium", "low"


class RPNMatrixPoint(BaseModel):
    """Simplified RPN point for matrix distribution"""
    gravity: int
    occurrence: int
    rpn_value: int

class RPNRankingResponse(BaseModel):
    """Complete RPN ranking response"""
    total_failure_modes: int
    critical_count: int  # RPN >= 200
    high_count: int  # 100 <= RPN < 200
    medium_count: int  # 50 <= RPN < 100
    low_count: int  # RPN < 50
    ranking: List[RPNRankingItem]
    matrix_data: List[RPNMatrixPoint]
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== SKILL SCHEMAS ====================

class SkillBase(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    difficulty_level: int = Field(1, ge=1, le=5)
    certification_required: bool = False
    is_active: bool = True


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    skill_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    certification_required: Optional[bool] = None
    is_active: Optional[bool] = None


class SkillResponse(SkillBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== TECHNICIAN SKILL SCHEMAS ====================

class TechnicianSkillBase(BaseModel):
    technician_id: int
    skill_id: int
    proficiency_level: int = Field(1, ge=1, le=5, description="Niveau de compétence (1-5)")
    acquisition_date: Optional[date] = None
    certification_date: Optional[date] = None
    certification_expiry: Optional[date] = None
    is_validated: bool = False
    validated_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class TechnicianSkillCreate(BaseModel):
    skill_id: int
    proficiency_level: int = Field(1, ge=1, le=5)
    acquisition_date: Optional[date] = None
    certification_date: Optional[date] = None
    certification_expiry: Optional[date] = None
    notes: Optional[str] = None


class TechnicianSkillUpdate(BaseModel):
    proficiency_level: Optional[int] = Field(None, ge=1, le=5)
    acquisition_date: Optional[date] = None
    certification_date: Optional[date] = None
    certification_expiry: Optional[date] = None
    is_validated: Optional[bool] = None
    validated_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class TechnicianSkillResponse(TechnicianSkillBase):
    id: int
    skill_name: Optional[str] = None
    skill_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== EQUIPMENT REQUIRED SKILL SCHEMAS ====================

class EquipmentRequiredSkillBase(BaseModel):
    equipment_id: int
    skill_id: int
    required_proficiency_level: int = Field(3, ge=1, le=5, description="Niveau minimum requis")
    is_mandatory: bool = True
    priority: int = Field(1, ge=1, le=10)
    notes: Optional[str] = None


class EquipmentRequiredSkillCreate(BaseModel):
    skill_id: int
    required_proficiency_level: int = Field(3, ge=1, le=5)
    is_mandatory: bool = True
    priority: int = Field(1, ge=1, le=10)
    notes: Optional[str] = None


class EquipmentRequiredSkillUpdate(BaseModel):
    required_proficiency_level: Optional[int] = Field(None, ge=1, le=5)
    is_mandatory: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class EquipmentRequiredSkillResponse(EquipmentRequiredSkillBase):
    id: int
    skill_name: Optional[str] = None
    skill_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== TRAINING PRIORITY SCHEMAS ====================


# ==================== OCR EXTRACTION SCHEMAS ====================

class OcrExtractionBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    content: str
    format: str = Field(..., max_length=20)

class OcrExtractionCreate(OcrExtractionBase):
    pass

class OcrExtractionResponse(OcrExtractionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TrainingPriorityItem(BaseModel):
    """Item in training priority ranking"""
    equipment_id: int
    equipment_designation: str
    skill_id: int
    skill_name: str
    skill_category: Optional[str] = None
    required_proficiency_level: int
    
    # Risk metrics
    latest_rpn: int
    risk_level: str  # "critical", "high", "medium", "low"
    
    # Skill gap analysis
    num_technicians_with_skill: int
    num_technicians_needed: int
    skill_gap_percentage: float
    
    # Priority calculation
    priority_score: float  # Calculated based on RPN and skill gap
    priority_rank: int  # Overall ranking
    
    # Additional context
    is_mandatory_skill: bool
    certification_required: bool


class TrainingPriorityResponse(BaseModel):
    """Complete training priority response"""
    total_priorities: int
    critical_priorities: int  # High RPN + high skill gap
    equipment_analyzed: int
    skills_analyzed: int
    priorities: List[TrainingPriorityItem]
    generated_at: datetime = Field(default_factory=datetime.now)
    filters_applied: Dict[str, Any] = {}


# ==================== FORMATION PRIORITY SCHEMAS ====================

class PriorityLevel(str, Enum):
    """
    Priority classification based on TPS percentile thresholds.
    
    Classification Logic:
        - HIGH: TPS >= P90 (top 10% most critical)
        - MEDIUM: P50 <= TPS < P90 (above average)
        - LOW: TPS < P50 (below average)
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FormationPriorityItem(BaseModel):
    """
    Single formation priority result for a panne type.
    
    Contains all metrics contributing to the Training Priority Score (TPS),
    enabling full transparency and explainability for academic defense.
    """
    type_panne: str = Field(..., description="Failure type identifier")
    training_priority_score: float = Field(..., description="Calculated TPS (higher = more urgent)")
    priority_level: PriorityLevel = Field(..., description="Classification: HIGH/MEDIUM/LOW")
    
    # Component metrics (for explainability)
    rpn_average: float = Field(..., description="Average RPN from AMDEC failure modes")
    frequency: int = Field(..., description="Number of interventions in the period")
    difficulty_rate: float = Field(..., ge=0, le=1, description="Ratio: problematic / total")
    safety_factor: float = Field(..., description="Applied safety multiplier")
    
    # Training recommendation
    recommended_training: str = Field(..., description="Suggested training program")
    
    # Supporting metadata
    failure_modes_count: int = Field(0, description="Number of linked AMDEC failure modes")
    total_interventions: int = Field(0, description="Total interventions analyzed")
    problematic_interventions: int = Field(0, description="Cancelled + delayed interventions")


class FormationPriorityResponse(BaseModel):
    """
    Complete response for formation priority analysis.
    """
    priorities: List[FormationPriorityItem] = Field(
        ..., 
        description="Ranked list of panne types by TPS (highest first)"
    )
    total_panne_types: int = Field(..., description="Number of distinct panne types analyzed")
    high_priority_count: int = Field(0, description="Count of HIGH priority items")
    medium_priority_count: int = Field(0, description="Count of MEDIUM priority items")
    low_priority_count: int = Field(0, description="Count of LOW priority items")
    period_start: Optional[date] = Field(None, description="Analysis period start")
    period_end: Optional[date] = Field(None, description="Analysis period end")
    generated_at: datetime = Field(default_factory=datetime.now)
    thresholds_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Percentile thresholds used for classification"
    )


class FormationPriorityNormalizedItem(BaseModel):
    """Normalized TPS for chart visualization (0-100 scale)."""
    type_panne: str
    training_priority_score: float
    normalized_score: float = Field(..., ge=0, le=100, description="0-100 normalized score")
    priority_level: PriorityLevel


class FormationPriorityNormalizedResponse(BaseModel):
    """Response with normalized TPS values for dashboard charts."""
    priorities: List[FormationPriorityNormalizedItem]
    min_tps: float
    max_tps: float
    generated_at: datetime = Field(default_factory=datetime.now)


class FormationPriorityComparisonItem(BaseModel):
    """Before/after comparison for training effectiveness."""
    type_panne: str
    tps_before: float
    tps_after: float
    tps_change: float = Field(..., description="Absolute change (after - before)")
    tps_change_percent: float = Field(..., description="Percentage change")
    priority_before: PriorityLevel
    priority_after: PriorityLevel
    improved: bool = Field(..., description="True if TPS decreased (improvement)")


class FormationPriorityComparisonResponse(BaseModel):
    """Response for before/after training comparison."""
    comparisons: List[FormationPriorityComparisonItem]
    period_before: Dict[str, Any]
    period_after: Dict[str, Any]
    total_improved: int = Field(0, description="Count of panne types that improved")
    total_degraded: int = Field(0, description="Count of panne types that degraded")
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== KNOWLEDGE BASE SCHEMAS ====================

class KnowledgeBaseDocumentBase(BaseModel):
    title: str = Field(..., max_length=500)
    category: str = Field(..., max_length=100, description="Formation, Safety, Enterprise, AMDEC")
    type_panne: Optional[str] = Field(None, max_length=100)
    content: str = Field(..., description="Markdown content")
    safety_level: str = Field("Low", description="High, Medium, Low")


class KnowledgeBaseDocumentCreate(KnowledgeBaseDocumentBase):
    pass


class KnowledgeBaseDocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    type_panne: Optional[str] = None
    content: Optional[str] = None
    safety_level: Optional[str] = None


class KnowledgeBaseDocumentResponse(KnowledgeBaseDocumentBase):
    id: int
    version: int
    indexed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseDocumentListResponse(BaseModel):
    items: List[KnowledgeBaseDocumentResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== COPILOT SCHEMAS ====================

class CopilotIntentEnum(str, Enum):
    """
    Supported intents for the Maintenance Copilot.
    
    - KPI_EXPLANATION: Explain maintenance KPIs (MTTR, MTBF, Availability) and trends
    - EQUIPMENT_HEALTH_SUMMARY: Provide equipment health assessment with risk classification
    - INTERVENTION_REPORT: Generate formal, audit-ready maintenance reports
    """
    KPI_EXPLANATION = "KPI_EXPLANATION"
    EQUIPMENT_HEALTH_SUMMARY = "EQUIPMENT_HEALTH_SUMMARY"
    INTERVENTION_REPORT = "INTERVENTION_REPORT"


class CopilotContext(BaseModel):
    """
    Optional context for Copilot queries.
    Provides additional information to narrow down the scope of analysis.
    """
    equipment_id: Optional[str] = Field(None, description="Equipment ID or designation")
    period: Optional[str] = Field(None, description="Time period (e.g., '2025-12', '2025-Q4')")
    intervention_id: Optional[int] = Field(None, description="Specific intervention ID for reports")


class CopilotQueryRequest(BaseModel):
    """
    Request schema for Copilot queries.
    
    The message should be a natural language question about maintenance KPIs,
    equipment health, or intervention details.
    """
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Natural language query for the Copilot"
    )
    context: Optional[CopilotContext] = Field(
        None,
        description="Optional context to scope the query"
    )


class CopilotRecommendedAction(BaseModel):
    """
    A recommended action from the Copilot with priority and rationale.
    All recommendations are data-driven and justified.
    """
    action: str = Field(..., description="Specific action to take")
    priority: str = Field(..., pattern="^(high|medium|low)$", description="Action priority")
    rationale: str = Field(..., description="Data-backed rationale for this action")


class CopilotSupportingData(BaseModel):
    """
    Reference to supporting data used in the Copilot's analysis.
    Ensures transparency and traceability of all facts.
    """
    data_type: str = Field(..., description="Type of data: kpi, intervention, amdec, equipment")
    reference_id: Optional[str] = Field(None, description="ID of the referenced entity")
    value: Optional[str] = Field(None, description="The actual value or metric")
    description: str = Field(..., description="Human-readable description of the data point")


class CopilotQueryResponse(BaseModel):
    """
    Structured response from the Maintenance Copilot.
    
    All responses include:
    - Detected intent
    - Summary and detailed explanation
    - Supporting data references (for traceability)
    - Recommended actions (when applicable)
    - Confidence level
    """
    intent: CopilotIntentEnum = Field(..., description="Detected intent from the query")
    summary: str = Field(..., description="Brief summary of the analysis")
    detailed_explanation: str = Field(..., description="Comprehensive explanation with reasoning")
    supporting_data_references: List[CopilotSupportingData] = Field(
        default=[],
        description="List of data points used in the analysis"
    )
    recommended_actions: List[CopilotRecommendedAction] = Field(
        default=[],
        description="Actionable recommendations based on the analysis"
    )
    confidence_level: str = Field(
        ..., 
        pattern="^(high|medium|low)$",
        description="Confidence in the analysis based on data availability"
    )
    limitations: Optional[str] = Field(
        None,
        description="Any limitations or missing data that affected the analysis"
    )


# ==================== GUIDANCE AGENT SCHEMAS ====================

class GuidanceContext(BaseModel):
    """
    User context for guidance queries.
    Tracks current page, role, and recent actions for context-aware assistance.
    """
    current_page: str = Field(..., description="Current page route (e.g., '/home/equipment')")
    user_role: Optional[str] = Field(None, description="User role (admin, technician, viewer)")
    recent_actions: List[str] = Field(default=[], description="List of recent user actions")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation tracking")


class GuidanceAskRequest(BaseModel):
    """
    Request schema for guidance questions.
    
    Users can ask natural language questions about:
    - How to use the system
    - Where to find specific features
    - How to perform certain tasks
    """
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="User's natural language question"
    )
    context: GuidanceContext = Field(..., description="User context for personalized guidance")


class GuidanceSuggestedAction(BaseModel):
    """
    A suggested next action for the user.
    """
    action_name: str = Field(..., description="Short, clear action name (imperative)")
    description: str = Field(..., description="Brief description of what this action does")
    priority: str = Field(..., pattern="^(high|medium|low)$", description="Action priority")
    ui_element: Optional[str] = Field(None, description="UI element to interact with (e.g., 'Create Button')")
    target_route: Optional[str] = Field(None, description="Target page route if navigation is needed")


class GuidanceRelatedLink(BaseModel):
    """
    Related page or documentation link.
    """
    title: str = Field(..., description="Link title")
    route: str = Field(..., description="Page route or URL")
    description: Optional[str] = Field(None, description="Brief description of what the link leads to")


class GuidanceAskResponse(BaseModel):
    """
    Response schema for guidance questions.
    """
    answer: str = Field(..., description="Natural language answer to the user's question")
    suggested_actions: List[GuidanceSuggestedAction] = Field(
        default=[],
        description="Suggested next actions based on the question"
    )
    related_links: List[GuidanceRelatedLink] = Field(
        default=[],
        description="Related pages or documentation"
    )
    confidence: str = Field(
        ...,
        pattern="^(high|medium|low)$",
        description="Confidence in the answer"
    )
    response_type: str = Field(
        ...,
        pattern="^(how_to|navigation|feature_explanation|troubleshooting|general)$",
        description="Type of guidance provided"
    )


class SuggestActionRequest(BaseModel):
    """
    Request schema for action suggestions based on current page.
    """
    current_page: str = Field(..., description="Current page route")
    user_role: Optional[str] = Field(None, description="User role")
    user_intent: Optional[str] = Field(None, description="Optional user intent (e.g., 'create work order')")


class SuggestActionResponse(BaseModel):
    """
    Response schema for action suggestions.
    """
    suggestions: List[GuidanceSuggestedAction] = Field(
        ...,
        description="List of suggested actions for the current page"
    )
    page_name: str = Field(..., description="Human-readable page name")
    page_description: Optional[str] = Field(None, description="Brief description of the current page")


class PageHelpResponse(BaseModel):
    """
    Response schema for page-specific help.
    """
    page_name: str = Field(..., description="Human-readable page name")
    description: str = Field(..., description="Overview of what this page is for")
    key_features: List[str] = Field(..., description="Key features available on this page")
    common_tasks: List[str] = Field(..., description="Common tasks users perform on this page")
    available_actions: List[GuidanceSuggestedAction] = Field(
        ...,
        description="All available actions on this page"
    )
    tips: List[str] = Field(default=[], description="Helpful tips for using this page")


class ExplainErrorRequest(BaseModel):
    """
    Request schema for error explanation.
    """
    error_message: str = Field(..., min_length=1, max_length=1000, description="Error message to explain")
    context: GuidanceContext = Field(..., description="Context where the error occurred")
    error_code: Optional[str] = Field(None, description="Error code if available")


class RecoveryStep(BaseModel):
    """
    A step to recover from an error.
    """
    step_number: int = Field(..., description="Step number in the recovery process")
    instruction: str = Field(..., description="What the user should do")
    ui_element: Optional[str] = Field(None, description="UI element to interact with")


class ExplainErrorResponse(BaseModel):
    """
    Response schema for error explanation.
    """
    simplified_explanation: str = Field(
        ...,
        description="User-friendly explanation of what went wrong"
    )
    likely_cause: str = Field(..., description="Most likely cause of this error")
    recovery_steps: List[RecoveryStep] = Field(
        ...,
        description="Step-by-step instructions to fix the error"
    )
    prevention_tip: Optional[str] = Field(None, description="How to avoid this error in the future")
    severity: str = Field(
        ...,
        pattern="^(critical|warning|info)$",
        description="Error severity level"
    )

