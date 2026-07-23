import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import UploadedFile, User
from app.schemas.file import FileRead

router = APIRouter(prefix="/files", tags=["files"])


def _get_owned_file(db: Session, file_id: uuid.UUID, owner_id: uuid.UUID) -> UploadedFile:
    file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.owner_id == owner_id)
        .first()
    )
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


@router.post("/", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    upload: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadedFile:
    upload.file.seek(0, 2)
    size_bytes = upload.file.tell()
    upload.file.seek(0)

    if size_bytes > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb}MB upload limit",
        )

    storage_key = storage.build_storage_key(current_user.id, upload.filename or "file")
    storage.upload_fileobj(
        upload.file,
        storage_key,
        upload.content_type or "application/octet-stream",
    )

    file = UploadedFile(
        owner_id=current_user.id,
        filename=upload.filename or "file",
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_key=storage_key,
    )
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


@router.get("/", response_model=list[FileRead])
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UploadedFile]:
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.owner_id == current_user.id)
        .order_by(UploadedFile.created_at.desc())
        .all()
    )


@router.get("/{file_id}", response_model=FileRead)
def get_file_metadata(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadedFile:
    return _get_owned_file(db, file_id, current_user.id)


@router.get("/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    file = _get_owned_file(db, file_id, current_user.id)
    body = storage.download_fileobj(file.storage_key)
    return StreamingResponse(
        body.iter_chunks(),
        media_type=file.content_type,
        headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    file = _get_owned_file(db, file_id, current_user.id)
    storage.delete_object(file.storage_key)
    db.delete(file)
    db.commit()
