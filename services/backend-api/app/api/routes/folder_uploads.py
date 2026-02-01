"""
Folder Upload API Routes

Provides endpoints for uploading folder hierarchies as data sources.
Supports init/upload/complete workflow for large folder uploads.
"""
from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form, Query
from typing import List, Optional, Dict, Any
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from botocore.exceptions import ClientError

from app.models.folder_upload import (
    FolderUpload,
    FolderUploadStatus,
    FolderFileEntry,
    FolderUploadInitRequest,
    FolderUploadInitResponse,
    FolderFileUploadRequest,
    BatchUploadResponse,
    FolderUploadCompleteResponse,
    FolderFileListResponse,
    FolderFileResponse,
    FolderUploadResponse,
)
from app.models.data_source import (
    DataSource,
    DataSourceType,
    DataSourceStatus,
    DataSourceResponse,
)
from app.models.project import Project
from app.utils.file_validation import (
    validate_folder_structure,
    validate_file,
    validate_relative_path,
    get_content_type,
    is_preview_supported,
    calculate_depth,
    get_parent_path,
    MAX_FILE_SIZE,
    MAX_FOLDER_SIZE,
    MAX_FOLDER_DEPTH,
    MAX_FILES_PER_FOLDER,
)
from app.utils.s3_utils import (
    upload_folder_file,
    upload_folder_manifest,
    generate_presigned_download_url,
    delete_folder_file as s3_delete_folder_file,
    delete_folder_upload as s3_delete_folder_upload,
    get_folder_upload_prefix,
    get_folder_file_s3_key,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["folder-uploads"])


def build_file_tree(files: List[FolderFileEntry]) -> Dict[str, Any]:
    """
    Build a tree structure from a list of files for the file browser UI.

    Args:
        files: List of FolderFileEntry objects

    Returns:
        Tree structure dict with nested directories and files
    """
    tree = {"name": "/", "type": "directory", "children": {}}

    for file_entry in files:
        parts = file_entry.relative_path.split("/")
        current = tree["children"]

        # Navigate/create directories
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {
                    "name": part,
                    "type": "directory",
                    "path": "/".join(parts[: i + 1]),
                    "children": {},
                }
            current = current[part]["children"]

        # Add the file
        filename = parts[-1]
        current[filename] = {
            "name": filename,
            "type": "file",
            "path": file_entry.relative_path,
            "id": file_entry.id,
            "size": file_entry.file_size,
            "content_type": file_entry.content_type,
            "extension": file_entry.file_extension,
        }

    return tree


@router.post(
    "/projects/{project_id}/data-sources/folder-upload/init",
    response_model=FolderUploadInitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def init_folder_upload(
    project_id: str,
    name: str = Form(..., min_length=1, max_length=100),
    root_folder_name: str = Form(..., min_length=1, max_length=255),
    category: str = Form(default="document"),
    total_files: int = Form(..., ge=1, le=MAX_FILES_PER_FOLDER),
    total_size: int = Form(..., ge=1, le=MAX_FOLDER_SIZE),
    max_depth: int = Form(..., ge=0, le=MAX_FOLDER_DEPTH),
    description: Optional[str] = Form(default=None),
):
    """
    Initialize a folder upload session.

    Creates a FolderUpload document and returns an upload_id for subsequent
    file upload requests. Validates size and depth limits.

    Args:
        project_id: The project ID
        name: User-friendly name for the data source
        root_folder_name: Original folder name being uploaded
        category: Category (document, code, data)
        total_files: Expected total number of files
        total_size: Expected total size in bytes
        max_depth: Maximum directory depth
        description: Optional description

    Returns:
        FolderUploadInitResponse with upload_id and s3_prefix
    """
    # Validate project exists
    project = await Project.find_one({"_id": project_id})
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Validate category
    if category not in ["document", "code", "data"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category must be one of: document, code, data",
        )

    # Validate limits
    if total_size > MAX_FOLDER_SIZE:
        max_mb = MAX_FOLDER_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total folder size exceeds {max_mb:.0f}MB limit",
        )

    if max_depth > MAX_FOLDER_DEPTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder depth exceeds {MAX_FOLDER_DEPTH} levels limit",
        )

    if total_files > MAX_FILES_PER_FOLDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder contains more than {MAX_FILES_PER_FOLDER} files",
        )

    # Create upload ID
    upload_id = str(uuid.uuid4())

    # Generate S3 prefix
    s3_prefix = get_folder_upload_prefix(project_id, upload_id)

    # Create FolderUpload document
    folder_upload = FolderUpload(
        id=upload_id,
        project_id=project_id,
        name=name,
        root_folder_name=root_folder_name,
        category=category,
        total_files=total_files,
        total_size=total_size,
        max_depth=max_depth,
        status=FolderUploadStatus.UPLOADING,
        s3_prefix=s3_prefix,
        files=[],
    )

    await folder_upload.insert()

    logger.info(
        f"Initialized folder upload {upload_id} for project {project_id}: "
        f"{total_files} files, {total_size} bytes"
    )

    return FolderUploadInitResponse(
        upload_id=upload_id,
        project_id=project_id,
        s3_prefix=s3_prefix,
        status="uploading",
        message=f"Folder upload initialized. Upload your files to complete.",
    )


@router.post(
    "/projects/{project_id}/data-sources/folder-upload/{upload_id}/files",
    response_model=BatchUploadResponse,
)
async def upload_folder_files(
    project_id: str,
    upload_id: str,
    files: List[UploadFile] = File(...),
    relative_paths: str = Form(...),  # JSON array of paths
):
    """
    Upload a batch of files to a folder upload session.

    Files are uploaded to S3 with their relative paths preserved.
    Can be called multiple times to upload files in batches.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID from init
        files: List of files to upload
        relative_paths: JSON array of relative paths corresponding to files

    Returns:
        BatchUploadResponse with upload status for each file
    """
    import json

    # Limit JSON size to prevent DoS attacks
    MAX_PATHS_JSON_SIZE = 256 * 1024  # 256KB
    if len(relative_paths) > MAX_PATHS_JSON_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relative_paths JSON too large (max 256KB)",
        )

    # Parse relative paths
    try:
        paths = json.loads(relative_paths)
        if not isinstance(paths, list):
            raise ValueError("relative_paths must be a JSON array")
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid relative_paths JSON format",
        )

    if len(files) != len(paths):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Number of files ({len(files)}) must match number of paths ({len(paths)})",
        )

    MAX_FILES_PER_BATCH = 50
    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size ({len(files)}) exceeds maximum ({MAX_FILES_PER_BATCH})",
        )

    # Find the folder upload
    folder_upload = await FolderUpload.find_one(
        {"_id": upload_id, "project_id": project_id}
    )
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    if folder_upload.status == FolderUploadStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder upload has already been completed",
        )
    if folder_upload.status == FolderUploadStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder upload is in an error state and cannot accept new files",
        )
    if folder_upload.status != FolderUploadStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder upload is not in uploading state (current: {folder_upload.status})",
        )

    results = []
    files_uploaded = 0
    files_failed = 0
    total_size_uploaded = 0
    new_file_entries = []

    for i, (file, relative_path) in enumerate(zip(files, paths)):
        try:
            # Validate relative path
            path_result = validate_relative_path(relative_path)
            if not path_result.valid:
                results.append(
                    {
                        "path": relative_path,
                        "status": "error",
                        "error": path_result.error,
                    }
                )
                files_failed += 1
                continue

            # Read file content
            file_data = await file.read()
            file_size = len(file_data)

            # Validate file
            filename = os.path.basename(relative_path)
            file_result = validate_file(filename, file_size, folder_upload.category)
            if not file_result.valid:
                results.append(
                    {
                        "path": relative_path,
                        "status": "error",
                        "error": file_result.error,
                    }
                )
                files_failed += 1
                continue

            # Determine content type
            content_type = get_content_type(filename)

            # Upload to S3
            s3_result = await upload_folder_file(
                file_data=file_data,
                project_id=project_id,
                upload_id=upload_id,
                relative_path=relative_path,
                content_type=content_type,
            )

            # Create file entry
            file_entry = FolderFileEntry(
                id=str(uuid.uuid4()),
                relative_path=relative_path,
                filename=filename,
                file_extension=Path(filename).suffix.lower(),
                file_size=file_size,
                content_type=content_type,
                s3_key=s3_result["s3_key"],
                s3_url=s3_result["s3_url"],
                depth=calculate_depth(relative_path),
                parent_path=get_parent_path(relative_path),
                checksum=s3_result.get("checksum"),
            )

            new_file_entries.append(file_entry)
            files_uploaded += 1
            total_size_uploaded += file_size

            results.append(
                {
                    "path": relative_path,
                    "status": "success",
                    "file_id": file_entry.id,
                    "size": file_size,
                }
            )

        except ClientError as e:
            logger.error(f"S3 error uploading file {relative_path}: {str(e)}")
            results.append(
                {"path": relative_path, "status": "error", "error": "Failed to upload file to storage"}
            )
            files_failed += 1
        except Exception as e:
            logger.error(f"Error uploading file {relative_path}: {str(e)}", exc_info=True)
            results.append(
                {"path": relative_path, "status": "error", "error": "Internal server error during upload"}
            )
            files_failed += 1

    # Update folder upload with new files
    if new_file_entries:
        folder_upload.files.extend(new_file_entries)
        folder_upload.updated_at = datetime.now(timezone.utc)
        await folder_upload.save()

    logger.info(
        f"Uploaded {files_uploaded} files to folder upload {upload_id}, "
        f"failed: {files_failed}, size: {total_size_uploaded} bytes"
    )

    return BatchUploadResponse(
        upload_id=upload_id,
        files_uploaded=files_uploaded,
        files_failed=files_failed,
        total_size=total_size_uploaded,
        results=results,
    )


@router.post(
    "/projects/{project_id}/data-sources/folder-upload/{upload_id}/complete",
    response_model=FolderUploadCompleteResponse,
)
async def complete_folder_upload(
    project_id: str,
    upload_id: str,
    description: Optional[str] = Form(default=None),
):
    """
    Complete a folder upload and create the DataSource entry.

    Validates that files were uploaded, creates the manifest,
    and creates the DataSource document.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID
        description: Optional description for the data source

    Returns:
        FolderUploadCompleteResponse with data_source_id
    """
    # Find the folder upload
    folder_upload = await FolderUpload.find_one(
        {"_id": upload_id, "project_id": project_id}
    )
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    if folder_upload.status != FolderUploadStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder upload is not in uploading state (current: {folder_upload.status})",
        )

    if not folder_upload.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were uploaded. Upload files before completing.",
        )

    # Update folder upload status
    folder_upload.status = FolderUploadStatus.PROCESSING
    await folder_upload.save()

    try:
        # Calculate actual totals
        actual_total_files = len(folder_upload.files)
        actual_total_size = sum(f.file_size for f in folder_upload.files)
        actual_max_depth = max(f.depth for f in folder_upload.files) if folder_upload.files else 0

        # Update folder upload with actual values
        folder_upload.total_files = actual_total_files
        folder_upload.total_size = actual_total_size
        folder_upload.max_depth = actual_max_depth

        # Create manifest
        manifest_data = {
            "version": "1.0",
            "upload_id": upload_id,
            "project_id": project_id,
            "root_folder_name": folder_upload.root_folder_name,
            "category": folder_upload.category,
            "created_at": folder_upload.created_at.isoformat(),
            "total_files": actual_total_files,
            "total_size": actual_total_size,
            "max_depth": actual_max_depth,
            "files": [
                {
                    "id": f.id,
                    "relative_path": f.relative_path,
                    "filename": f.filename,
                    "s3_key": f.s3_key,
                    "size": f.file_size,
                    "content_type": f.content_type,
                    "checksum": f.checksum,
                }
                for f in folder_upload.files
            ],
        }

        # Upload manifest to S3
        await upload_folder_manifest(project_id, upload_id, manifest_data)

        # Create DataSource
        data_source_id = str(uuid.uuid4())
        data_source = DataSource(
            id=data_source_id,
            project_id=project_id,
            type=DataSourceType.FOLDER_UPLOAD,
            name=folder_upload.name,
            configuration={
                "folder_upload_id": upload_id,
                "root_folder_name": folder_upload.root_folder_name,
                "category": folder_upload.category,
                "total_files": actual_total_files,
                "total_size": actual_total_size,
                "max_depth": actual_max_depth,
                "s3_prefix": folder_upload.s3_prefix,
                "description": description,
            },
            status=DataSourceStatus.CONNECTED,
        )

        await data_source.insert()

        # Update folder upload with data source ID and status
        folder_upload.data_source_id = data_source_id
        folder_upload.status = FolderUploadStatus.READY
        folder_upload.updated_at = datetime.now(timezone.utc)
        await folder_upload.save()

        logger.info(
            f"Completed folder upload {upload_id} -> data source {data_source_id}: "
            f"{actual_total_files} files, {actual_total_size} bytes"
        )

        return FolderUploadCompleteResponse(
            upload_id=upload_id,
            data_source_id=data_source_id,
            status="ready",
            total_files=actual_total_files,
            total_size=actual_total_size,
            message="Folder upload completed successfully",
        )

    except Exception as e:
        # Mark as error
        folder_upload.status = FolderUploadStatus.ERROR
        folder_upload.error_message = "Upload completion failed. Please try again or contact support."
        await folder_upload.save()

        logger.error(f"Error completing folder upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete folder upload. Please try again or contact support.",
        )


@router.get(
    "/projects/{project_id}/data-sources/{data_source_id}/files",
    response_model=FolderFileListResponse,
)
async def list_folder_files(
    project_id: str,
    data_source_id: str,
    path: Optional[str] = Query(default=None, description="Filter by directory path"),
    include_tree: bool = Query(default=True, description="Include tree structure"),
):
    """
    List files in a folder upload data source.

    Returns files with optional tree structure for the file browser UI.

    Args:
        project_id: The project ID
        data_source_id: The data source ID
        path: Optional path prefix to filter files
        include_tree: Whether to include tree structure

    Returns:
        FolderFileListResponse with files and optional tree
    """
    # Find the data source
    data_source = await DataSource.find_one(
        {"_id": data_source_id, "project_id": project_id}
    )
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {data_source_id} not found",
        )

    if data_source.type != DataSourceType.FOLDER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is not a folder upload",
        )

    # Get folder upload
    upload_id = data_source.configuration.get("folder_upload_id")
    folder_upload = await FolderUpload.find_one({"_id": upload_id})
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    # Filter files by path if specified
    files = folder_upload.files
    if path:
        path_normalized = path.rstrip("/")
        files = [f for f in files if f.relative_path.startswith(path_normalized + "/") or f.relative_path == path_normalized]

    # Build response
    files_data = [
        {
            "id": f.id,
            "relative_path": f.relative_path,
            "filename": f.filename,
            "file_extension": f.file_extension,
            "file_size": f.file_size,
            "content_type": f.content_type,
            "depth": f.depth,
            "parent_path": f.parent_path,
            "preview_supported": is_preview_supported(f.filename),
            "created_at": f.created_at.isoformat(),
        }
        for f in files
    ]

    # Build tree if requested
    tree = build_file_tree(files) if include_tree else None

    return FolderFileListResponse(
        data_source_id=data_source_id,
        upload_id=upload_id,
        root_folder_name=folder_upload.root_folder_name,
        total_files=len(files),
        total_size=sum(f.file_size for f in files),
        files=files_data,
        tree=tree,
    )


@router.get(
    "/projects/{project_id}/data-sources/{data_source_id}/files/{file_id}",
    response_model=FolderFileResponse,
)
async def get_folder_file(
    project_id: str,
    data_source_id: str,
    file_id: str,
    download: bool = Query(default=False, description="Generate download URL"),
):
    """
    Get details of a single file in a folder upload.

    Args:
        project_id: The project ID
        data_source_id: The data source ID
        file_id: The file ID
        download: Whether to generate a download URL

    Returns:
        FolderFileResponse with file details and download URL
    """
    # Find the data source
    data_source = await DataSource.find_one(
        {"_id": data_source_id, "project_id": project_id}
    )
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {data_source_id} not found",
        )

    if data_source.type != DataSourceType.FOLDER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is not a folder upload",
        )

    # Get folder upload
    upload_id = data_source.configuration.get("folder_upload_id")
    folder_upload = await FolderUpload.find_one({"_id": upload_id})
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    # Find the file
    file_entry = next((f for f in folder_upload.files if f.id == file_id), None)
    if not file_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found",
        )

    # Generate download URL
    download_url = await generate_presigned_download_url(
        file_entry.s3_key,
        filename=file_entry.filename if download else None,
    )

    return FolderFileResponse(
        id=file_entry.id,
        relative_path=file_entry.relative_path,
        filename=file_entry.filename,
        file_extension=file_entry.file_extension,
        file_size=file_entry.file_size,
        content_type=file_entry.content_type,
        download_url=download_url,
        preview_supported=is_preview_supported(file_entry.filename),
        created_at=file_entry.created_at.isoformat(),
    )


@router.delete(
    "/projects/{project_id}/data-sources/{data_source_id}/files/{file_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_folder_file(
    project_id: str,
    data_source_id: str,
    file_id: str,
):
    """
    Delete a single file from a folder upload.

    Args:
        project_id: The project ID
        data_source_id: The data source ID
        file_id: The file ID to delete

    Returns:
        Success message
    """
    # Find the data source
    data_source = await DataSource.find_one(
        {"_id": data_source_id, "project_id": project_id}
    )
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {data_source_id} not found",
        )

    if data_source.type != DataSourceType.FOLDER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is not a folder upload",
        )

    # Get folder upload
    upload_id = data_source.configuration.get("folder_upload_id")
    folder_upload = await FolderUpload.find_one({"_id": upload_id})
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    # Find the file
    file_entry = next((f for f in folder_upload.files if f.id == file_id), None)
    if not file_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found",
        )

    # Remove from DB first to prevent race conditions
    folder_upload.files = [f for f in folder_upload.files if f.id != file_id]
    folder_upload.total_files = len(folder_upload.files)
    folder_upload.total_size = sum(f.file_size for f in folder_upload.files)
    folder_upload.updated_at = datetime.now(timezone.utc)
    await folder_upload.save()

    # Update data source configuration
    data_source.configuration["total_files"] = folder_upload.total_files
    data_source.configuration["total_size"] = folder_upload.total_size
    data_source.updated_at = datetime.now(timezone.utc)
    await data_source.save()

    # Delete from S3 after DB update
    await s3_delete_folder_file(
        project_id=project_id,
        upload_id=upload_id,
        relative_path=file_entry.relative_path,
    )

    logger.info(
        f"Deleted file {file_id} ({file_entry.relative_path}) from folder upload {upload_id}"
    )

    return {"message": f"File {file_entry.filename} deleted successfully"}


@router.get(
    "/projects/{project_id}/data-sources/folder-upload/{upload_id}",
    response_model=FolderUploadResponse,
)
async def get_folder_upload(
    project_id: str,
    upload_id: str,
):
    """
    Get details of a folder upload session.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID

    Returns:
        FolderUploadResponse with upload details
    """
    folder_upload = await FolderUpload.find_one(
        {"_id": upload_id, "project_id": project_id}
    )
    if not folder_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder upload {upload_id} not found",
        )

    return FolderUploadResponse(
        id=folder_upload.id,
        project_id=folder_upload.project_id,
        data_source_id=folder_upload.data_source_id,
        name=folder_upload.name,
        root_folder_name=folder_upload.root_folder_name,
        category=folder_upload.category,
        total_files=len(folder_upload.files),
        total_size=sum(f.file_size for f in folder_upload.files),
        max_depth=folder_upload.max_depth,
        status=folder_upload.status.value,
        created_at=folder_upload.created_at.isoformat(),
        updated_at=folder_upload.updated_at.isoformat(),
    )
