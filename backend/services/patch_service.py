"""
Service for managing patches and applying changes
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database import Project, PendingPatch, Change, UndoBuffer
from ..models import ApplyChangesRequest, ChangeRequest

class PatchService:
    
    async def apply_changes(self, changes: List[ChangeRequest], db: Session) -> Dict[str, Any]:
        """Apply accepted changes to the project"""
        
        # Get the project (assuming single project for now)
        project = db.query(Project).first()
        if not project:
            raise ValueError("No project found")
        
        # Create undo buffer before applying changes
        await self._create_undo_buffer(project, db)
        
        # Get accepted changes
        change_ids = [c.change_id for c in changes if c.accepted]
        accepted_changes = db.query(Change).filter(
            and_(
                Change.id.in_(change_ids),
                Change.accepted == True
            )
        ).all()
        
        if not accepted_changes:
            return {"success": True, "project_id": str(project.id), "changes_applied": 0}
        
        # Apply changes to LaTeX content
        new_content = await self._apply_changes_to_latex(project.resume_tex, accepted_changes)
        
        # Update project
        project.resume_tex = new_content
        project.compile_status = "pending"
        
        # Mark patch as applied
        patch_ids = list(set([str(change.patch_id) for change in accepted_changes]))
        db.query(PendingPatch).filter(
            PendingPatch.id.in_(patch_ids)
        ).update({"status": "applied"})
        
        # Mark rejected changes as discarded
        rejected_ids = [c.change_id for c in changes if not c.accepted]
        db.query(Change).filter(
            Change.id.in_(rejected_ids)
        ).update({"accepted": False})
        
        # Mark patch as discarded if all changes rejected
        for patch_id in patch_ids:
            remaining_changes = db.query(Change).filter(
                and_(
                    Change.patch_id == patch_id,
                    Change.accepted != False
                )
            ).count()
            
            if remaining_changes == 0:
                db.query(PendingPatch).filter(
                    PendingPatch.id == patch_id
                ).update({"status": "discarded"})
        
        db.commit()
        
        return {
            "success": True,
            "project_id": str(project.id),
            "changes_applied": len(accepted_changes)
        }

    async def _create_undo_buffer(self, project: Project, db: Session):
        """Create undo buffer before applying changes"""
        
        # Remove old undo buffer
        db.query(UndoBuffer).filter(
            UndoBuffer.project_id == project.id
        ).delete()
        
        # Create new undo buffer
        undo_buffer = UndoBuffer(
            project_id=project.id,
            resume_tex_snapshot=project.resume_tex
        )
        db.add(undo_buffer)

    async def _apply_changes_to_latex(self, original_tex: str, changes: List[Change]) -> str:
        """Apply changes to LaTeX content"""
        
        lines = original_tex.split('\n')
        
        # Sort changes by line number (reverse order to maintain indices)
        sorted_changes = sorted(changes, key=lambda x: x.start_line, reverse=True)
        
        for change in sorted_changes:
            start_idx = change.start_line - 1  # Convert to 0-indexed
            end_idx = change.end_line
            
            if change.type == "addition":
                # Insert new content
                new_lines = change.content.split('\n')
                lines[start_idx:start_idx] = new_lines
                
            elif change.type == "removal":
                # Remove content
                if start_idx < len(lines) and end_idx <= len(lines):
                    del lines[start_idx:end_idx]
        
        return '\n'.join(lines)

    async def get_project(self, project_id: str, db: Session) -> Optional[Project]:
        """Get project by ID"""
        return db.query(Project).filter(Project.id == project_id).first()

    async def undo_last_apply(self, project_id: str, db: Session) -> Dict[str, Any]:
        """Undo the last apply operation"""
        
        project = await self.get_project(project_id, db)
        if not project:
            raise ValueError("Project not found")
        
        # Get undo buffer
        undo_buffer = db.query(UndoBuffer).filter(
            UndoBuffer.project_id == project.id
        ).first()
        
        if not undo_buffer:
            raise ValueError("No undo buffer found")
        
        # Restore content
        project.resume_tex = undo_buffer.resume_tex_snapshot
        project.compile_status = "pending"
        
        # Clear undo buffer
        db.delete(undo_buffer)
        
        db.commit()
        
        return {
            "success": True,
            "project_id": project_id,
            "message": "Undo successful"
        }

    async def get_pending_changes(self, project_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get all pending changes for a project"""
        
        changes = db.query(Change).join(PendingPatch).filter(
            and_(
                PendingPatch.project_id == project_id,
                PendingPatch.status == "proposed",
                Change.accepted.is_(None)
            )
        ).all()
        
        return [
            {
                "id": str(change.id),
                "type": change.type,
                "start_line": change.start_line,
                "end_line": change.end_line,
                "content": change.content,
                "accepted": change.accepted,
                "pdf_regions": change.pdf_regions or []
            }
            for change in changes
        ]

    async def accept_change(self, change_id: str, accepted: bool, db: Session) -> Dict[str, Any]:
        """Accept or reject a specific change"""
        
        change = db.query(Change).filter(Change.id == change_id).first()
        if not change:
            raise ValueError("Change not found")
        
        change.accepted = accepted
        db.commit()
        
        return {
            "success": True,
            "change_id": change_id,
            "accepted": accepted
        }

    async def get_patch_summary(self, project_id: str, db: Session) -> Dict[str, Any]:
        """Get summary of all patches for a project"""
        
        patches = db.query(PendingPatch).filter(
            PendingPatch.project_id == project_id
        ).all()
        
        summary = {
            "total_patches": len(patches),
            "proposed": 0,
            "applied": 0,
            "discarded": 0,
            "total_changes": 0,
            "pending_changes": 0,
            "accepted_changes": 0,
            "rejected_changes": 0
        }
        
        for patch in patches:
            summary[f"{patch.status}"] += 1
            
            changes = db.query(Change).filter(Change.patch_id == patch.id).all()
            summary["total_changes"] += len(changes)
            
            for change in changes:
                if change.accepted is None:
                    summary["pending_changes"] += 1
                elif change.accepted:
                    summary["accepted_changes"] += 1
                else:
                    summary["rejected_changes"] += 1
        
        return summary
