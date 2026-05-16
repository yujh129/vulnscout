from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vulnscout.models.db import get_db
from vulnscout.models.schemas import Patch, PatchStatus, PatchResponse

router = APIRouter()


@router.post("/{patch_id}/apply", response_model=PatchResponse)
async def apply_patch_endpoint(patch_id: str, db: Session = Depends(get_db)):
    """Apply a patch (mark as applied)."""
    patch = db.query(Patch).filter(Patch.id == patch_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    patch.status = PatchStatus.APPLIED
    db.commit()
    return PatchResponse.model_validate(patch)


@router.post("/{patch_id}/reject", response_model=PatchResponse)
async def reject_patch(patch_id: str, db: Session = Depends(get_db)):
    """Reject a patch."""
    patch = db.query(Patch).filter(Patch.id == patch_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    patch.status = PatchStatus.REJECTED
    db.commit()
    return PatchResponse.model_validate(patch)
