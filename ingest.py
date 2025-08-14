"""
ScholarBot Document Ingestion Module
Handles file upload, validation, and batch processing
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import hashlib
import mimetypes

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Handles document ingestion and validation"""

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md'}
    MAX_FILE_SIZE_MB = 50  # Will be overridden by config

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_path = Path(config['storage']['data_path'])
        self.max_file_size_mb = config['app']['upload_limit_mb']
        self.max_documents = config['app']['max_documents']

        # Create data directory
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Initialize file tracking
        self.processed_files = self._get_processed_files()

    def _get_processed_files(self) -> Dict[str, str]:
        """Get list of already processed files with their hashes"""
        processed_files = {}

        if self.data_path.exists():
            for file_path in self.data_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    file_hash = self._get_file_hash(str(file_path))
                    processed_files[str(file_path)] = file_hash

        return processed_files

    def _get_file_hash(self, file_path: str) -> str:
        """Get SHA-256 hash of file content"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ Error hashing file {file_path}: {e}")
            return ""

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """Validate a single file"""
        file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"

        # Check file extension
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file type: {file_path.suffix}. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return False, f"File too large: {file_size_mb:.1f}MB (max: {self.max_file_size_mb}MB)"

        # Check MIME type (basic validation using mimetypes)
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            valid_mimes = {
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.md': 'text/plain'
            }

            expected_mime = valid_mimes.get(file_path.suffix.lower())
            if expected_mime and mime_type and not mime_type.startswith(expected_mime.split('/')[0]):
                logger.warning(f"⚠️ MIME type mismatch for {file_path}: expected {expected_mime}, got {mime_type}")

        except Exception as e:
            logger.warning(f"⚠️ Could not check MIME type for {file_path}: {e}")

        return True, "Valid file"

    def validate_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Validate multiple files"""
        valid_files = []
        invalid_files = []
        total_size_mb = 0

        for file_path in file_paths:
            is_valid, message = self.validate_file(file_path)

            if is_valid:
                file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
                total_size_mb += file_size_mb
                valid_files.append({
                    'path': file_path,
                    'size_mb': file_size_mb,
                    'name': Path(file_path).name
                })
            else:
                invalid_files.append({
                    'path': file_path,
                    'error': message,
                    'name': Path(file_path).name
                })

        # Check total upload size
        if total_size_mb > self.max_file_size_mb:
            return {
                'success': False,
                'message': f"Total upload size ({total_size_mb:.1f}MB) exceeds limit ({self.max_file_size_mb}MB)",
                'valid_files': [],
                'invalid_files': invalid_files,
                'total_size_mb': total_size_mb
            }

        # Check document count limit
        current_doc_count = len(self.processed_files)
        if current_doc_count + len(valid_files) > self.max_documents:
            return {
                'success': False,
                'message': f"Would exceed document limit ({self.max_documents}). Current: {current_doc_count}, Adding: {len(valid_files)}",
                'valid_files': valid_files,
                'invalid_files': invalid_files,
                'total_size_mb': total_size_mb
            }

        return {
            'success': len(valid_files) > 0,
            'message': f"Validated {len(valid_files)} valid files, {len(invalid_files)} invalid files",
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'total_size_mb': total_size_mb
        }

    def copy_files_to_data_dir(self, file_paths: List[str]) -> List[str]:
        """Copy files to data directory and return new paths"""
        copied_paths = []

        for file_path in file_paths:
            try:
                src_path = Path(file_path)

                # Check for duplicates using hash
                file_hash = self._get_file_hash(str(src_path))

                # Check if file already exists (by hash)
                duplicate_found = False
                for existing_path, existing_hash in self.processed_files.items():
                    if existing_hash == file_hash:
                        logger.info(
                            f"⚠️ Duplicate file detected: {src_path.name} (already exists as {Path(existing_path).name})")
                        copied_paths.append(existing_path)  # Use existing file
                        duplicate_found = True
                        break

                if duplicate_found:
                    continue

                # Generate unique filename if needed
                dst_path = self.data_path / src_path.name
                counter = 1
                while dst_path.exists():
                    name_parts = src_path.stem, counter, src_path.suffix
                    dst_path = self.data_path / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                    counter += 1

                # Copy file
                shutil.copy2(src_path, dst_path)
                copied_paths.append(str(dst_path))

                # Update processed files tracking
                self.processed_files[str(dst_path)] = file_hash

                logger.info(f"✅ Copied {src_path.name} to {dst_path.name}")

            except Exception as e:
                logger.error(f"❌ Error copying {file_path}: {e}")

        return copied_paths

    def ingest_from_folder(self, folder_path: str) -> Dict[str, Any]:
        """Ingest all supported files from a folder"""
        folder_path = Path(folder_path)

        if not folder_path.exists() or not folder_path.is_dir():
            return {
                'success': False,
                'message': f"Invalid folder path: {folder_path}"
            }

        # Find all supported files
        found_files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            found_files.extend(folder_path.glob(f"**/*{ext}"))

        file_paths = [str(f) for f in found_files]

        if not file_paths:
            return {
                'success': False,
                'message': f"No supported files found in {folder_path}"
            }

        logger.info(f"📁 Found {len(file_paths)} files in {folder_path}")

        # Validate files
        validation_result = self.validate_files(file_paths)

        if not validation_result['success']:
            return validation_result

        # Copy valid files
        valid_file_paths = [f['path'] for f in validation_result['valid_files']]
        copied_paths = self.copy_files_to_data_dir(valid_file_paths)

        return {
            'success': True,
            'message': f"Successfully ingested {len(copied_paths)} files from folder",
            'file_paths': copied_paths,
            'validation_result': validation_result
        }

    def ingest_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Main ingestion method for file lists"""
        if not file_paths:
            return {
                'success': False,
                'message': "No files provided"
            }

        # Validate files
        validation_result = self.validate_files(file_paths)

        if not validation_result['success']:
            return validation_result

        # Copy valid files to data directory
        valid_file_paths = [f['path'] for f in validation_result['valid_files']]
        copied_paths = self.copy_files_to_data_dir(valid_file_paths)

        return {
            'success': True,
            'message': f"Successfully ingested {len(copied_paths)} files",
            'file_paths': copied_paths,
            'validation_result': validation_result
        }

    def get_ingested_files(self) -> List[Dict[str, Any]]:
        """Get list of all ingested files with metadata"""
        files = []

        for file_path in self.processed_files:
            try:
                path = Path(file_path)
                if path.exists():
                    stat = path.stat()
                    files.append({
                        'name': path.name,
                        'path': str(path),
                        'size_mb': stat.st_size / (1024 * 1024),
                        'type': path.suffix.lower(),
                        'modified': stat.st_mtime
                    })
            except Exception as e:
                logger.error(f"❌ Error getting file info for {file_path}: {e}")

        return sorted(files, key=lambda x: x['modified'], reverse=True)

    def remove_file(self, file_path: str) -> bool:
        """Remove a file from data directory"""
        try:
            path = Path(file_path)
            if path.exists() and path.parent == self.data_path:
                path.unlink()
                # Remove from tracking
                if str(path) in self.processed_files:
                    del self.processed_files[str(path)]
                logger.info(f"✅ Removed file: {path.name}")
                return True
            else:
                logger.error(f"❌ File not found or not in data directory: {file_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Error removing file {file_path}: {e}")
            return False

    def clear_all_files(self) -> bool:
        """Remove all files from data directory"""
        try:
            if self.data_path.exists():
                shutil.rmtree(self.data_path)
                self.data_path.mkdir(parents=True, exist_ok=True)
                self.processed_files = {}
                logger.info("✅ Cleared all ingested files")
                return True
        except Exception as e:
            logger.error(f"❌ Error clearing files: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        files = self.get_ingested_files()
        total_size_mb = sum(f['size_mb'] for f in files)

        type_counts = {}
        for f in files:
            file_type = f['type']
            type_counts[file_type] = type_counts.get(file_type, 0) + 1

        return {
            'total_files': len(files),
            'total_size_mb': total_size_mb,
            'type_breakdown': type_counts,
            'data_path': str(self.data_path),
            'max_files': self.max_documents,
            'max_size_mb': self.max_file_size_mb
        }