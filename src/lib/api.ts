/**
 * API client for connecting to Python backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Change {
  id: string;
  type: 'addition' | 'removal';
  startLine: number;
  endLine: number;
  content: string;
  accepted: boolean | null;
  pdfRegions?: Array<{x: number, y: number, width: number, height: number}>;
}

export interface Project {
  id: string;
  resume_tex: string;
  compile_status: string;
  outline: Record<string, any>;
}

export interface IngestResponse {
  project_id: string;
  resume_tex: string;
  pdf_url: string;
  reconstruction_note?: string;
}

export interface PatchResponse {
  patch_id: string;
  changes: Change[];
  project_id: string;
}

export interface ApplyChangesRequest {
  changes: Array<{
    change_id: string;
    accepted: boolean;
  }>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} ${error}`);
    }

    return response.json();
  }

  async uploadResume(file: File): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/ingest`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Upload Error: ${response.status} ${error}`);
    }

    return response.json();
  }

  async generatePatch(instruction: string, codeSlice?: string, fullDocument: boolean = false, projectId?: string, projectData?: any): Promise<PatchResponse> {
    return this.request<PatchResponse>('/llm/patch', {
      method: 'POST',
      body: JSON.stringify({
        instruction,
        code_slice: codeSlice,
        full_document: fullDocument,
        project_id: projectId,
        project_data: projectData,
      }),
    });
  }

  async applyChanges(request: ApplyChangesRequest): Promise<{success: boolean; project_id: string}> {
    return this.request<{success: boolean; project_id: string}>('/changes/apply', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/project/${projectId}`);
  }

  async getPdfUrl(projectId: string): Promise<string> {
    return `${this.baseUrl}/artifact/pdf/${projectId}`;
  }

  async healthCheck(): Promise<{status: string; service: string}> {
    return this.request<{status: string; service: string}>('/health');
  }
}

export const apiClient = new ApiClient();
