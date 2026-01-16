import { SupabaseClient } from '@supabase/supabase-js';

const API_URL = process.env.NEXT_PUBLIC_GMAO_API_URL || 'http://localhost:8000/api';

export class GmaoApiClient {
    private supabase: SupabaseClient;

    constructor(supabase: SupabaseClient) {
        this.supabase = supabase;
    }

    private async getHeaders(): Promise<HeadersInit> {
        const { data: { session } } = await this.supabase.auth.getSession();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };

        if (session?.access_token) {
            headers['Authorization'] = `Bearer ${session.access_token}`;
        }

        return headers;
    }

    async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const headers = await this.getHeaders();
        const config = {
            ...options,
            headers: {
                ...headers,
                ...options.headers,
            },
        };

        const url = `${API_URL}${endpoint}`;
        console.log(`Fetching URL: ${url}`);
        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        return response.json();
    }

    // ==================== KPI ====================
    async getStats() {
        return this.fetch<any>('/stats');
    }

    async getKpiDashboard() {
        return this.fetch<any>('/kpi/dashboard');
    }

    async getMonthlyKpis(params?: { start_date?: string; end_date?: string; equipment_id?: number }) {
        const query = new URLSearchParams();
        if (params?.start_date) query.append('start_date', params.start_date);
        if (params?.end_date) query.append('end_date', params.end_date);
        if (params?.equipment_id) query.append('equipment_id', params.equipment_id.toString());
        return this.fetch<any>(`/kpi/monthly-equipment-kpis?${query.toString()}`);
    }

    async getFailureDistribution() {
        return this.fetch<any>('/kpi/failure-rate');
    }

    async getCostAnalysis() {
        return this.fetch<any>('/kpi/cost-analysis');
    }

    // ==================== Equipment ====================
    async listEquipment(params?: { skip?: number; limit?: number }) {
        const query = new URLSearchParams();
        if (params?.skip) query.append('skip', params.skip.toString());
        if (params?.limit) query.append('limit', params.limit.toString());

        return this.fetch<any[]>(`/equipment/?${query.toString()}`);
    }

    async getEquipment(id: number) {
        return this.fetch<any>(`/equipment/${id}`);
    }

    async updateEquipment(id: number, data: any) {
        return this.fetch<any>(`/equipment/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteEquipment(id: number, force: boolean = false) {
        return this.fetch<any>(`/equipment/${id}?force=${force}`, {
            method: 'DELETE'
        });
    }

    async getEquipmentPredictions(id: number, kpiType: 'mtbf' | 'mttr' | 'availability') {
        return this.fetch<any>('/ml/predict', {
            method: 'POST',
            body: JSON.stringify({
                kpi_type: kpiType,
                equipment_id: id,
                return_confidence: true
            })
        });
    }

    // ==================== Interventions ====================
    async listInterventions(params?: { status?: string; equipment_id?: number }) {
        const query = new URLSearchParams();
        if (params?.status) query.append('status', params.status);
        if (params?.equipment_id) query.append('equipment_id', params.equipment_id.toString());

        return this.fetch<any[]>(`/interventions/?${query.toString()}`);
    }

    async getIntervention(id: number) {
        return this.fetch<any>(`/interventions/${id}`);
    }

    async createIntervention(data: any) {
        return this.fetch<any>('/interventions/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateIntervention(id: number, data: any) {
        return this.fetch<any>(`/interventions/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteIntervention(id: number) {
        return this.fetch<any>(`/interventions/${id}`, {
            method: 'DELETE'
        });
    }

    // ==================== RAG ====================
    async queryRag(query: string, options?: {
        useCache?: boolean;
        topK?: number;
        similarityThreshold?: number;
        includeSources?: boolean;
    }) {
        return this.fetch<any>('/rag/query/v2', {
            method: 'POST',
            body: JSON.stringify({
                query,
                use_cache: options?.useCache ?? true,
                top_k: options?.topK ?? 5,
                similarity_threshold: options?.similarityThreshold ?? 0.02,
                include_sources: options?.includeSources ?? true
            })
        });
    }

    async uploadDocument(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = await this.getHeaders();
        delete (headers as Record<string, string>)['Content-Type']; // Let browser set multipart boundary

        const response = await fetch(`${API_URL}/rag/upload`, {
            method: 'POST',
            headers: {
                'Authorization': (headers as Record<string, string>)['Authorization'] || '',
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        return response.json();
    }

    // ==================== Spare Parts ====================
    async listSpareParts(params?: { skip?: number; limit?: number }) {
        const query = new URLSearchParams();
        if (params?.skip) query.append('skip', params.skip.toString());
        if (params?.limit) query.append('limit', params.limit.toString());
        return this.fetch<any[]>(`/spare-parts/?${query.toString()}`);
    }

    async getSparePart(id: number) {
        return this.fetch<any>(`/spare-parts/${id}`);
    }

    async updateSparePart(id: number, data: any) {
        return this.fetch<any>(`/spare-parts/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteSparePart(id: number) {
        return this.fetch<any>(`/spare-parts/${id}`, {
            method: 'DELETE'
        });
    }

    // ==================== Technicians ====================
    async listTechnicians(params?: { skip?: number; limit?: number }) {
        const query = new URLSearchParams();
        if (params?.skip) query.append('skip', params.skip.toString());
        if (params?.limit) query.append('limit', params.limit.toString());
        return this.fetch<any[]>(`/technicians/?${query.toString()}`);
    }

    async getTechnician(id: number) {
        return this.fetch<any>(`/technicians/${id}`);
    }

    async updateTechnician(id: number, data: any) {
        return this.fetch<any>(`/technicians/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteTechnician(id: number, force: boolean = false) {
        return this.fetch<any>(`/technicians/${id}?force=${force}`, {
            method: 'DELETE'
        });
    }

    // ==================== Import/Export ====================
    // ==================== Import/Export ====================

    // --- Exports ---

    /**
     * Export Interventions
     */
    async exportInterventions(
        format: 'csv' | 'excel' = 'csv',
        filters?: {
            equipment_id?: number;
            start_date?: string;
            end_date?: string;
            type_panne?: string
        }
    ) {
        const params = new URLSearchParams({ format });
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());
        if (filters?.start_date) params.append('start_date', filters.start_date);
        if (filters?.end_date) params.append('end_date', filters.end_date);
        if (filters?.type_panne) params.append('type_panne', filters.type_panne);

        return this.fetchBlob(`/export/interventions?${params.toString()}`);
    }

    /**
     * Export Equipment
     */
    async exportEquipment(
        format: 'csv' | 'excel' = 'csv',
        includeStats: boolean = true
    ) {
        const params = new URLSearchParams({
            format,
            include_stats: includeStats.toString()
        });
        return this.fetchBlob(`/export/equipment?${params.toString()}`);
    }

    /**
     * Export Spare Parts
     */
    async exportSpareParts(
        format: 'csv' | 'excel' = 'csv',
        lowStockOnly: boolean = false
    ) {
        const params = new URLSearchParams({
            format,
            low_stock_only: lowStockOnly.toString()
        });
        return this.fetchBlob(`/export/spare-parts?${params.toString()}`);
    }

    /**
     * Export KPI Report
     */
    async exportKpiReport(
        format: 'excel' | 'pdf' = 'excel',
        filters?: {
            start_date?: string;
            end_date?: string;
            equipment_id?: number
        }
    ) {
        const params = new URLSearchParams({ format });
        if (filters?.start_date) params.append('start_date', filters.start_date);
        if (filters?.end_date) params.append('end_date', filters.end_date);
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());

        return this.fetchBlob(`/export/kpi-report?${params.toString()}`);
    }

    /**
     * Export AMDEC Report
     */
    async exportAmdecReport(
        format: 'excel' | 'pdf' = 'excel',
        filters?: {
            risk_level?: string;
            equipment_id?: number
        }
    ) {
        const params = new URLSearchParams({ format });
        if (filters?.risk_level) params.append('risk_level', filters.risk_level);
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());

        return this.fetchBlob(`/export/amdec-report?${params.toString()}`);
    }

    // --- Imports ---

    async importAmdec(file: File) {
        return this.uploadImportFile('/import/amdec', file);
    }

    async importGmao(file: File) {
        return this.uploadImportFile('/import/gmao', file);
    }

    async importWorkload(file: File) {
        return this.uploadImportFile('/import/workload', file);
    }

    /**
     * Helper to handle file upload for imports
     */
    private async uploadImportFile(endpoint: string, file: File) {
        const formData = new FormData();
        formData.append('file', file);
        // Default user for now, can be updated to use actual user context if needed
        const urlWithUser = `${endpoint}?user_id=system`;

        const headers = await this.getHeaders();
        // Remove Content-Type to let browser handle multipart/form-data boundary
        const { 'Content-Type': _, ...authHeaders } = headers as Record<string, string>;

        const response = await fetch(`${API_URL}${urlWithUser}`, {
            method: 'POST',
            headers: authHeaders,
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Import failed: ${errorText || response.statusText}`);
        }
        return response.json();
    }

    // ==================== OCR ====================
    async ocrProcess(file: File, outputFormat: 'markdown' | 'html' | 'json' | 'text' = 'markdown') {
        const formData = new FormData();
        formData.append('file', file);

        const headers = await this.getHeaders();
        const response = await fetch(`${API_URL}/ocr/${outputFormat}`, {
            method: 'POST',
            headers: {
                'Authorization': (headers as Record<string, string>)['Authorization'] || '',
            },
            body: formData
        });
        if (!response.ok) {
            throw new Error(`OCR failed: ${response.statusText}`);
        }
        return outputFormat === 'json' ? response.json() : response.text();
    }

    async listOcrExtractions() {
        return this.fetch<any[]>('/ocr/extractions');
    }

    async saveOcrExtraction(data: { filename: string; content: string; format: string }) {
        return this.fetch<any>('/ocr/extractions', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async deleteOcrExtraction(id: number) {
        return this.fetch<any>(`/ocr/extractions/${id}`, {
            method: 'DELETE'
        });
    }

    // ==================== AMDEC - Failure Modes ====================
    async listFailureModes(params?: {
        equipment_id?: number;
        is_active?: boolean;
        include_rpn?: boolean;
        skip?: number;
        limit?: number
    }) {
        const query = new URLSearchParams();
        if (params?.equipment_id) query.append('equipment_id', params.equipment_id.toString());
        if (params?.is_active !== undefined) query.append('is_active', params.is_active.toString());
        if (params?.include_rpn !== undefined) query.append('include_rpn', params.include_rpn.toString());
        if (params?.skip) query.append('skip', params.skip.toString());
        if (params?.limit) query.append('limit', params.limit.toString());
        return this.fetch<any[]>(`/amdec/failure-modes?${query.toString()}`);
    }

    async getFailureMode(id: number) {
        return this.fetch<any>(`/amdec/failure-modes/${id}`);
    }

    async createFailureMode(data: {
        equipment_id: number;
        mode_name: string;
        description?: string;
        failure_cause?: string;
        failure_effect?: string;
        detection_method?: string;
        prevention_action?: string;
    }) {
        return this.fetch<any>('/amdec/failure-modes', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateFailureMode(id: number, data: Partial<{
        mode_name: string;
        description: string;
        failure_cause: string;
        failure_effect: string;
        detection_method: string;
        prevention_action: string;
        is_active: boolean;
    }>) {
        return this.fetch<any>(`/amdec/failure-modes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteFailureMode(id: number) {
        return this.fetch<any>(`/amdec/failure-modes/${id}`, {
            method: 'DELETE'
        });
    }

    // ==================== AMDEC - RPN Analysis ====================
    async listRpnAnalyses(params?: {
        failure_mode_id?: number;
        equipment_id?: number;
        min_rpn?: number;
        action_status?: string;
        skip?: number;
        limit?: number;
    }) {
        const query = new URLSearchParams();
        if (params?.failure_mode_id) query.append('failure_mode_id', params.failure_mode_id.toString());
        if (params?.equipment_id) query.append('equipment_id', params.equipment_id.toString());
        if (params?.min_rpn) query.append('min_rpn', params.min_rpn.toString());
        if (params?.action_status) query.append('action_status', params.action_status);
        if (params?.skip) query.append('skip', params.skip.toString());
        if (params?.limit) query.append('limit', params.limit.toString());
        return this.fetch<any[]>(`/amdec/rpn-analyses?${query.toString()}`);
    }

    async getRpnAnalysis(id: number) {
        return this.fetch<any>(`/amdec/rpn-analyses/${id}`);
    }

    async createRpnAnalysis(data: {
        failure_mode_id: number;
        gravity: number;
        occurrence: number;
        detection: number;
        analyst_name?: string;
        comments?: string;
        corrective_action?: string;
        action_due_date?: string;
    }) {
        return this.fetch<any>('/amdec/rpn-analyses', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateRpnAnalysis(id: number, data: Partial<{
        gravity: number;
        occurrence: number;
        detection: number;
        analyst_name: string;
        comments: string;
        corrective_action: string;
        action_status: string;
        action_due_date: string;
    }>) {
        return this.fetch<any>(`/amdec/rpn-analyses/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteRpnAnalysis(id: number) {
        return this.fetch<any>(`/amdec/rpn-analyses/${id}`, {
            method: 'DELETE'
        });
    }

    // ==================== AMDEC - Ranking & Analytics ====================
    async getRpnRanking(params?: {
        equipment_id?: number;
        min_rpn?: number;
        risk_levels?: string;
        limit?: number;
    }) {
        const query = new URLSearchParams();
        if (params?.equipment_id) query.append('equipment_id', params.equipment_id.toString());
        if (params?.min_rpn) query.append('min_rpn', params.min_rpn.toString());
        if (params?.risk_levels) query.append('risk_levels', params.risk_levels);
        if (params?.limit) query.append('limit', params.limit.toString());
        return this.fetch<any>(`/amdec/rpn-ranking?${query.toString()}`);
    }

    async getCriticalEquipment(minRpn: number = 200) {
        return this.fetch<any[]>(`/amdec/critical-equipment?min_rpn=${minRpn}`);
    }

    async getRecentInterventions(limit = 5) {
        return this.fetch<any[]>(`/interventions?limit=${limit}`);
    }

    async getKpiTrends(metric: string, granularity: string) {
        return this.fetch<any>(`/kpi/trends?metric=${metric}&granularity=${granularity}`);
    }

    async triggerAutoAmdec() {
        return this.fetch<any>('/amdec/auto-analyze', {
            method: 'POST'
        });
    }

    // ==================== Report Downloads ====================

    /**
     * Helper method to fetch binary data (Blob) from API
     */
    private async fetchBlob(endpoint: string): Promise<Blob> {
        const headers = await this.getHeaders();
        // Remove Content-Type for blob responses
        const { 'Content-Type': _, ...blobHeaders } = headers as Record<string, string>;

        const response = await fetch(`${API_URL}${endpoint}`, {
            headers: blobHeaders,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Download failed: ${errorText || response.statusText}`);
        }

        return response.blob();
    }

    /**
     * Download KPI report in Excel or PDF format
     */
    async downloadKpiReport(
        format: 'excel' | 'pdf',
        filters?: { start_date?: string; end_date?: string; equipment_id?: number }
    ): Promise<Blob> {
        const params = new URLSearchParams({ format });
        if (filters?.start_date) params.append('start_date', filters.start_date);
        if (filters?.end_date) params.append('end_date', filters.end_date);
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());

        return this.fetchBlob(`/export/kpi-report?${params.toString()}`);
    }

    /**
     * Download AMDEC/RPN analysis report in Excel or PDF format
     */
    async downloadAmdecReport(
        format: 'excel' | 'pdf',
        filters?: { risk_level?: string; equipment_id?: number }
    ): Promise<Blob> {
        const params = new URLSearchParams({ format });
        if (filters?.risk_level) params.append('risk_level', filters.risk_level);
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());

        return this.fetchBlob(`/export/amdec-report?${params.toString()}`);
    }

    /**
     * Download equipment report in CSV or Excel format
     */
    async downloadEquipmentReport(
        format: 'csv' | 'excel',
        includeStats: boolean = true
    ): Promise<Blob> {
        const params = new URLSearchParams({
            format,
            include_stats: includeStats.toString()
        });
        return this.fetchBlob(`/export/equipment?${params.toString()}`);
    }

    /**
     * Download interventions report in CSV or Excel format
     */
    async downloadInterventionsReport(
        format: 'csv' | 'excel',
        filters?: { equipment_id?: number; start_date?: string; end_date?: string; type_panne?: string }
    ): Promise<Blob> {
        const params = new URLSearchParams({ format });
        if (filters?.equipment_id) params.append('equipment_id', filters.equipment_id.toString());
        if (filters?.start_date) params.append('start_date', filters.start_date);
        if (filters?.end_date) params.append('end_date', filters.end_date);
        if (filters?.type_panne) params.append('type_panne', filters.type_panne);

        return this.fetchBlob(`/export/interventions?${params.toString()}`);
    }

    /**
     * Download spare parts inventory report in CSV or Excel format
     */
    async downloadSparePartsReport(
        format: 'csv' | 'excel',
        lowStockOnly: boolean = false
    ): Promise<Blob> {
        const params = new URLSearchParams({
            format,
            low_stock_only: lowStockOnly.toString()
        });
        return this.fetchBlob(`/export/spare-parts?${params.toString()}`);
    }
    // ==================== Formation Priority ====================
    async getFormationPriorities(params?: { start_date?: string; end_date?: string }) {
        const query = new URLSearchParams();
        if (params?.start_date) query.append('start_date', params.start_date);
        if (params?.end_date) query.append('end_date', params.end_date);
        return this.fetch<any>(`/formation-priority/by-panne-type?${query.toString()}`);
    }

    async getFormationPrioritiesNormalized(params?: { start_date?: string; end_date?: string }) {
        const query = new URLSearchParams();
        if (params?.start_date) query.append('start_date', params.start_date);
        if (params?.end_date) query.append('end_date', params.end_date);
        return this.fetch<any>(`/formation-priority/by-panne-type/normalized?${query.toString()}`);
    }

    async compareFormationPriorities(params: {
        before_start: string;
        before_end: string;
        after_start: string;
        after_end: string;
    }) {
        const query = new URLSearchParams();
        query.append('before_start', params.before_start);
        query.append('before_end', params.before_end);
        query.append('after_start', params.after_start);
        query.append('after_end', params.after_end);
        return this.fetch<any>(`/formation-priority/compare?${query.toString()}`);
    }

    // ==================== Knowledge Base ====================
    async listDocuments(params?: {
        page?: number;
        size?: number;
        category?: string;
        type_panne?: string;
        search?: string;
    }) {
        const query = new URLSearchParams();
        if (params?.page) query.append('page', params.page.toString());
        if (params?.size) query.append('size', params.size.toString());
        if (params?.category && params.category !== 'all') query.append('category', params.category);
        if (params?.type_panne && params.type_panne !== 'all') query.append('type_panne', params.type_panne);
        if (params?.search) query.append('search', params.search);

        return this.fetch<{
            items: any[];
            total: number;
            page: number;
            size: number;
            pages: number;
        }>(`/knowledge-base?${query.toString()}`);
    }

    async getDocument(id: number) {
        return this.fetch<any>(`/knowledge-base/${id}`);
    }

    async createDocument(data: {
        title: string;
        category: string;
        type_panne?: string;
        content: string;
        safety_level: string;
    }) {
        return this.fetch<any>('/knowledge-base/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateDocument(id: number, data: {
        title?: string;
        category?: string;
        type_panne?: string;
        content?: string;
        safety_level?: string;
    }) {
        return this.fetch<any>(`/knowledge-base/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteDocument(id: number) {
        return this.fetch<any>(`/knowledge-base/${id}`, {
            method: 'DELETE',
        });
    }

    async reindexDocument(id: number) {
        return this.fetch<any>(`/knowledge-base/${id}/reindex`, {
            method: 'POST',
        });
    }

    // ==================== Copilot ====================
    async queryCopilot(data: CopilotQueryRequest): Promise<CopilotQueryResponse> {
        return this.fetch<CopilotQueryResponse>('/copilot/query', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // ==================== Guidance Agent ====================
    async askGuidance(data: GuidanceAskRequest): Promise<GuidanceAskResponse> {
        return this.fetch<GuidanceAskResponse>('/guidance/ask', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async suggestActions(data: SuggestActionRequest): Promise<SuggestActionResponse> {
        return this.fetch<SuggestActionResponse>('/guidance/suggest-action', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getPageHelp(pageRoute: string): Promise<PageHelpResponse> {
        // Remove leading slash if present for the API call
        const route = pageRoute.startsWith('/') ? pageRoute.substring(1) : pageRoute;
        return this.fetch<PageHelpResponse>(`/guidance/page-help/${route}`);
    }

    async explainError(data: ExplainErrorRequest): Promise<ExplainErrorResponse> {
        return this.fetch<ExplainErrorResponse>('/guidance/explain-error', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // ==================== AI Forecast ====================
    async getForecast(equipmentId: number, horizonDays: number = 90): Promise<ForecastResponse> {
        return this.fetch<ForecastResponse>('/predict/forecast', {
            method: 'POST',
            body: JSON.stringify({
                equipment_id: equipmentId,
                horizon_days: horizonDays
            })
        });
    }
}

// Copilot Types
export enum CopilotIntentEnum {
    KPI_EXPLANATION = "KPI_EXPLANATION",
    EQUIPMENT_HEALTH_SUMMARY = "EQUIPMENT_HEALTH_SUMMARY",
    INTERVENTION_REPORT = "INTERVENTION_REPORT"
}

export interface CopilotContext {
    equipment_id?: string | number;
    period?: string;
    intervention_id?: number;
}

export interface CopilotQueryRequest {
    message: string;
    context?: CopilotContext;
}

// ==================== AI Forecast Types ====================
export interface ForecastResponse {
    equipment_id: number;
    rul: {
        predicted_rul_days: number | null;
        predicted_failure_date: string | null;
        model_used: string;
        rmse_accuracy: number;
        confidence_score: number;
    };
    mtbf_forecast: {
        forecast?: Array<{
            date: string;
            predicted_mtbf: number;
            lower_bound: number;
            upper_bound: number;
        }>;
        model?: string;
        error?: string;
    };
    predicted_downtime_30d: number;
    current_mttr: number;
}

export interface CopilotRecommendedAction {
    action: string;
    priority: 'high' | 'medium' | 'low';
    rationale: string;
}

export interface CopilotSupportingData {
    data_type: string;
    reference_id?: string;
    value?: string;
    description: string;
}

export interface CopilotQueryResponse {
    intent: CopilotIntentEnum; // Use the enum here
    summary: string;
    detailed_explanation: string;
    supporting_data_references: CopilotSupportingData[];
    recommended_actions: CopilotRecommendedAction[];
    confidence_level: 'high' | 'medium' | 'low';
    limitations?: string;
}

// ==================== Guidance Agent Types ====================

export interface GuidanceContext {
    current_page: string;
    user_role?: string;
    recent_actions?: string[];
    session_id?: string;
}

export interface GuidanceAskRequest {
    question: string;
    context: GuidanceContext;
}

export interface GuidanceSuggestedAction {
    action_name: string;
    description: string;
    priority: 'high' | 'medium' | 'low';
    ui_element?: string;
    target_route?: string;
}

export interface GuidanceRelatedLink {
    title: string;
    route: string;
    description?: string;
}

export interface GuidanceAskResponse {
    answer: string;
    suggested_actions: GuidanceSuggestedAction[];
    related_links: GuidanceRelatedLink[];
    confidence: 'high' | 'medium' | 'low';
    response_type: 'how_to' | 'navigation' | 'feature_explanation' | 'troubleshooting' | 'general';
}

export interface SuggestActionRequest {
    current_page: string;
    user_role?: string;
    user_intent?: string;
}

export interface SuggestActionResponse {
    suggestions: GuidanceSuggestedAction[];
    page_name: string;
    page_description?: string;
}

export interface PageHelpResponse {
    page_name: string;
    description: string;
    key_features: string[];
    common_tasks: string[];
    available_actions: GuidanceSuggestedAction[];
    tips: string[];
}

export interface RecoveryStep {
    step_number: number;
    instruction: string;
    ui_element?: string;
}

export interface ExplainErrorRequest {
    error_message: string;
    context: GuidanceContext;
    error_code?: string;
}

export interface ExplainErrorResponse {
    simplified_explanation: string;
    likely_cause: string;
    recovery_steps: RecoveryStep[];
    prevention_tip?: string;
    severity: 'critical' | 'warning' | 'info';
}


