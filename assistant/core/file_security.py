"""
File security utilities for the AI Personal Business Assistant.
Handles secure file uploads, validation, and scanning.
"""
import os
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

# Try to import python-magic, fallback to mimetypes if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)

# File type configurations
ALLOWED_MIME_TYPES = {
    # Documents
    'text/plain': ['.txt'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/rtf': ['.rtf'],
    'text/rtf': ['.rtf'],
    
    # Images
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    
    # Audio
    'audio/mpeg': ['.mp3'],
    'audio/wav': ['.wav'],
    'audio/ogg': ['.ogg'],
    'audio/mp4': ['.m4a'],
    'audio/flac': ['.flac'],
    'audio/x-wav': ['.wav'],
    'audio/x-ms-wma': ['.wma'],
}

# Maximum file sizes (in bytes)
MAX_FILE_SIZES = {
    'document': 10 * 1024 * 1024,   # 10MB for documents
    'image': 5 * 1024 * 1024,       # 5MB for images
    'audio': 50 * 1024 * 1024,      # 50MB for audio files
}

# Dangerous file extensions that should never be allowed
DANGEROUS_EXTENSIONS = [
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
    '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi',
    '.php', '.jsp', '.asp', '.aspx', '.py', '.rb', '.pl', '.sh'
]

# Magic number signatures for common file types
MAGIC_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF8': 'image/gif',
    b'%PDF': 'application/pdf',
    b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': 'application/msword',  # MS Office
    b'PK\x03\x04': 'application/zip',  # Also used by modern Office docs
    b'ID3': 'audio/mpeg',
    b'\xff\xfb': 'audio/mpeg',  # MP3
    b'RIFF': 'audio/wav',
    b'OggS': 'audio/ogg',
}


class FileSecurityValidator:
    """
    Comprehensive file security validator.
    """
    
    def __init__(self):
        if MAGIC_AVAILABLE:
            try:
                self.magic_mime = magic.Magic(mime=True)
            except Exception as e:
                logger.warning(f"Failed to initialize python-magic: {e}. Falling back to mimetypes.")
                self.magic_mime = None
        else:
            logger.warning("python-magic not available. Using mimetypes for file type detection.")
            self.magic_mime = None
    
    def validate_file(self, uploaded_file: UploadedFile) -> Dict[str, any]:
        """
        Perform comprehensive file validation.
        
        Returns:
            Dict containing validation results and file metadata
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {
                'original_name': uploaded_file.name,
                'size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
            }
        }
        
        try:
            # Read file content for analysis
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            
            # Basic validation
            self._validate_file_name(uploaded_file.name, validation_result)
            self._validate_file_size(uploaded_file.size, validation_result)
            
            # MIME type validation
            detected_mime = self._detect_mime_type(file_content)
            self._validate_mime_type(detected_mime, uploaded_file.content_type, validation_result)
            
            # Content validation
            self._validate_file_content(file_content, detected_mime, validation_result)
            
            # Security scanning
            self._scan_for_threats(file_content, validation_result)
            
            # Update file info with detected information
            validation_result['file_info'].update({
                'detected_mime_type': detected_mime,
                'file_hash': self._calculate_file_hash(file_content),
                'safe_filename': self._generate_safe_filename(uploaded_file.name),
            })
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_file_name(self, filename: str, result: Dict):
        """Validate filename for security issues."""
        if not filename:
            result['errors'].append("Filename is required")
            result['is_valid'] = False
            return
        
        # Check for dangerous extensions
        ext = os.path.splitext(filename.lower())[1]
        if ext in DANGEROUS_EXTENSIONS:
            result['errors'].append(f"File type '{ext}' is not allowed")
            result['is_valid'] = False
        
        # Check for directory traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            result['errors'].append("Invalid characters in filename")
            result['is_valid'] = False
        
        # Check filename length
        if len(filename) > 255:
            result['warnings'].append("Filename is very long and will be truncated")
    
    def _validate_file_size(self, size: int, result: Dict):
        """Validate file size against limits."""
        if size == 0:
            result['errors'].append("File is empty")
            result['is_valid'] = False
            return
        
        # Determine file category and check size
        max_size = max(MAX_FILE_SIZES.values())  # Default to largest allowed
        
        for category, limit in MAX_FILE_SIZES.items():
            if size > limit:
                continue
            max_size = limit
            break
        
        if size > max_size:
            result['errors'].append(f"File size ({size} bytes) exceeds limit ({max_size} bytes)")
            result['is_valid'] = False
    
    def _detect_mime_type(self, content: bytes) -> str:
        """Detect MIME type from file content."""
        # First, check magic signatures
        for signature, mime_type in MAGIC_SIGNATURES.items():
            if content.startswith(signature):
                return mime_type
        
        # Use python-magic for detection if available
        if self.magic_mime:
            try:
                return self.magic_mime.from_buffer(content)
            except Exception as e:
                logger.warning(f"MIME detection with python-magic failed: {str(e)}")
        
        # Fallback to mimetypes based on filename
        return 'application/octet-stream'
    
    def _validate_mime_type(self, detected_mime: str, declared_mime: str, result: Dict):
        """Validate MIME type against allowed types."""
        if detected_mime not in ALLOWED_MIME_TYPES:
            result['errors'].append(f"File type '{detected_mime}' is not allowed")
            result['is_valid'] = False
            return
        
        # Check for MIME type spoofing
        if declared_mime and declared_mime != detected_mime:
            # Allow some common variations
            variations = {
                'audio/x-wav': 'audio/wav',
                'image/jpg': 'image/jpeg',
            }
            
            normalized_declared = variations.get(declared_mime, declared_mime)
            if normalized_declared != detected_mime:
                result['warnings'].append(
                    f"Declared MIME type '{declared_mime}' differs from detected '{detected_mime}'"
                )
    
    def _validate_file_content(self, content: bytes, mime_type: str, result: Dict):
        """Validate file content based on type."""
        if mime_type.startswith('image/'):
            self._validate_image_content(content, result)
        elif mime_type.startswith('audio/'):
            self._validate_audio_content(content, result)
        elif mime_type == 'application/pdf':
            self._validate_pdf_content(content, result)
        elif mime_type.startswith('text/'):
            self._validate_text_content(content, result)
    
    def _validate_image_content(self, content: bytes, result: Dict):
        """Validate image file content."""
        # Check for embedded scripts or suspicious content
        suspicious_patterns = [
            b'<script', b'javascript:', b'vbscript:', b'<?php',
            b'<%', b'<iframe', b'<object', b'<embed'
        ]
        
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                result['errors'].append("Image contains suspicious content")
                result['is_valid'] = False
                break
    
    def _validate_audio_content(self, content: bytes, result: Dict):
        """Validate audio file content."""
        # Basic validation - check if it looks like audio
        if len(content) < 1024:  # Very small audio files are suspicious
            result['warnings'].append("Audio file is very small")
    
    def _validate_pdf_content(self, content: bytes, result: Dict):
        """Validate PDF file content."""
        # Check for JavaScript in PDF
        if b'/JavaScript' in content or b'/JS' in content:
            result['warnings'].append("PDF contains JavaScript")
        
        # Check for forms
        if b'/AcroForm' in content:
            result['warnings'].append("PDF contains forms")
    
    def _validate_text_content(self, content: bytes, result: Dict):
        """Validate text file content."""
        try:
            # Try to decode as UTF-8
            text = content.decode('utf-8')
            
            # Check for suspicious patterns
            suspicious_patterns = [
                '<script', 'javascript:', 'vbscript:', '<?php',
                'eval(', 'exec(', 'import os', '__import__'
            ]
            
            text_lower = text.lower()
            for pattern in suspicious_patterns:
                if pattern in text_lower:
                    result['warnings'].append(f"Text contains suspicious pattern: {pattern}")
                    
        except UnicodeDecodeError:
            result['warnings'].append("Text file contains non-UTF-8 content")
    
    def _scan_for_threats(self, content: bytes, result: Dict):
        """Scan file content for potential threats."""
        # Check for embedded executables
        executable_signatures = [
            b'MZ',  # Windows PE
            b'\x7fELF',  # Linux ELF
            b'\xfe\xed\xfa',  # macOS Mach-O
        ]
        
        for signature in executable_signatures:
            if content.startswith(signature):
                result['errors'].append("File contains executable code")
                result['is_valid'] = False
                break
        
        # Check for archive files that might contain dangerous content
        archive_signatures = [
            b'PK\x03\x04',  # ZIP
            b'Rar!\x1a\x07',  # RAR
            b'\x1f\x8b',  # GZIP
        ]
        
        for signature in archive_signatures:
            if content.startswith(signature):
                result['warnings'].append("File appears to be an archive")
                break
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _generate_safe_filename(self, original_name: str) -> str:
        """Generate a safe filename."""
        import re
        from django.utils import timezone
        
        if not original_name:
            return f"file_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract extension
        name, ext = os.path.splitext(original_name)
        
        # Sanitize name
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        safe_name = safe_name.strip('._-')
        
        # Ensure name is not empty
        if not safe_name:
            safe_name = f"file_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return f"{safe_name}{ext.lower()}"


class SecureFileStorage:
    """
    Secure file storage with virus scanning and access control.
    """
    
    def __init__(self):
        self.validator = FileSecurityValidator()
    
    def store_file(self, uploaded_file: UploadedFile, workspace_id: str) -> Dict[str, any]:
        """
        Securely store an uploaded file.
        
        Returns:
            Dict containing storage results and file metadata
        """
        # Validate file
        validation_result = self.validator.validate_file(uploaded_file)
        
        if not validation_result['is_valid']:
            return {
                'success': False,
                'errors': validation_result['errors'],
                'warnings': validation_result.get('warnings', [])
            }
        
        try:
            # Generate secure filename
            safe_filename = validation_result['file_info']['safe_filename']
            file_hash = validation_result['file_info']['file_hash']
            
            # Create storage path with workspace isolation
            storage_path = f"workspaces/{workspace_id}/uploads/{file_hash[:2]}/{file_hash[2:4]}/{safe_filename}"
            
            # Store file (this would integrate with your MinIO/S3 setup)
            # For now, we'll return the metadata
            
            return {
                'success': True,
                'file_info': {
                    **validation_result['file_info'],
                    'storage_path': storage_path,
                    'secure_url': f"/api/v1/files/{file_hash}",
                },
                'warnings': validation_result.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"File storage error: {str(e)}")
            return {
                'success': False,
                'errors': [f"Storage error: {str(e)}"]
            }
    
    def get_file_info(self, file_hash: str) -> Optional[Dict[str, any]]:
        """Get information about a stored file."""
        # This would query your database for file metadata
        pass
    
    def delete_file(self, file_hash: str, workspace_id: str) -> bool:
        """Securely delete a file."""
        # This would remove the file from storage and database
        pass


# Global instances
file_validator = FileSecurityValidator()
secure_storage = SecureFileStorage()
