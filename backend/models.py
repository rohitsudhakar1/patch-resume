"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProjectResponse(BaseModel):
    id: str
    resume_tex: str
    compile_status: str
    outline: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class ChangeRequest(BaseModel):
    change_id: str
    accepted: bool

class ApplyChangesRequest(BaseModel):
    changes: List[ChangeRequest]

class PatchRequest(BaseModel):
    instruction: str
    code_slice: Optional[str] = None
    full_document: bool = False

class IngestResponse(BaseModel):
    project_id: str
    resume_tex: str
    pdf_url: str
    reconstruction_note: Optional[str] = None

class PatchResponse(BaseModel):
    patch_id: str
    changes: List[Dict[str, Any]]
    project_id: str

class CompileResponse(BaseModel):
    success: bool
    pdf_path: Optional[str] = None
    synctex_path: Optional[str] = None
    error: Optional[str] = None

class SyncResponse(BaseModel):
    success: bool
    line_number: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    page: Optional[int] = None
    file: Optional[str] = None
    error: Optional[str] = None

class RepairResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    changes: Optional[List[str]] = None
    error: Optional[str] = None

class PatchSummary(BaseModel):
    total_patches: int
    proposed: int
    applied: int
    discarded: int
    total_changes: int
    pending_changes: int
    accepted_changes: int
    rejected_changes: int
