# Security Features and Guidelines

## Overview

The AI Personal Business Assistant implements comprehensive security measures to protect user data, prevent attacks, and ensure privacy compliance.

## Security Features Implemented

### 1. Request Security Middleware

- **Rate Limiting**: Protects against DoS attacks with configurable limits
  - General API: 60 requests/minute, 1000/hour
  - Messaging: 30 requests/minute
  - Audio uploads: 10 requests/minute
  - File uploads: 10 requests/minute

- **Request Size Limiting**: Prevents oversized requests
  - Standard requests: 10MB max
  - File uploads: 50MB max

- **Suspicious Pattern Detection**: Blocks requests containing:
  - Script injection attempts
  - Directory traversal patterns
  - Malicious code patterns

### 2. File Upload Security

- **File Type Validation**: Only allows specific file types
  - Documents: PDF, DOC, DOCX, RTF, TXT
  - Images: JPG, PNG, GIF, WEBP
  - Audio: MP3, WAV, OGG, M4A, FLAC

- **MIME Type Verification**: Validates actual file content vs declared type
- **Magic Number Validation**: Checks file signatures for authenticity
- **Content Scanning**: Scans files for embedded threats
- **Secure File Naming**: Prevents directory traversal and filename attacks
- **Hash-based Storage**: Organizes files using content hashes

### 3. Input Sanitization

- **HTML Sanitization**: Removes dangerous HTML tags and attributes
- **Text Sanitization**: Strips control characters and limits length
- **SQL Injection Prevention**: Uses Django ORM parameterized queries
- **XSS Protection**: Sanitizes user input and output

### 4. Security Headers

- **Content Security Policy (CSP)**: Prevents code injection
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-XSS-Protection**: Enables browser XSS filtering
- **Referrer Policy**: Controls referrer information
- **HSTS**: Enforces HTTPS connections

### 5. Data Privacy & GDPR Compliance

- **Data Anonymization**: Anonymizes personal data while preserving business value
- **Data Export**: Provides complete data portability (GDPR Article 20)
- **Data Deletion**: Supports both soft and hard deletion
- **Retention Policies**: Automatic cleanup of expired data
- **Privacy Reports**: Generates compliance reports

### 6. Authentication & Session Security

- **Secure Session Management**: Cryptographically secure session tokens
- **Session Validation**: Middleware validates all requests
- **Phone Number Validation**: E.164 format validation
- **Token Expiration**: Configurable session timeouts

### 7. Audit & Monitoring

- **Security Event Logging**: Comprehensive security event tracking
- **Failed Authentication Logging**: Tracks failed login attempts
- **Suspicious Activity Detection**: Monitors for unusual patterns
- **Data Access Logging**: Audit trail for data access

## Configuration

### Environment Variables

```env
# Security Settings
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECRET_KEY=your-secret-key-here

# Rate Limiting
RATELIMIT_ENABLE=true

# File Upload Limits
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
```

### Django Settings

Security-related settings are configured in `settings.py`:

- Security middleware order
- Content Security Policy rules
- Input sanitization rules
- Password validation requirements
- Security headers configuration

## Security Commands

### Security Audit

Run comprehensive security audit:

```bash
python manage.py security_audit --all --days 30
```

Options:
- `--check-sessions`: Check for suspicious session patterns
- `--check-uploads`: Check for suspicious file uploads
- `--check-messages`: Check for suspicious message patterns
- `--days N`: Analyze last N days (default: 7)
- `--output FILE`: Output report file

### Data Cleanup

Clean up expired data based on retention policies:

```python
from core.privacy import privacy_manager
result = privacy_manager.cleanup_expired_data()
```

### Data Export (GDPR)

Export all data for a contact:

```python
from core.privacy import privacy_manager
result = privacy_manager.export_personal_data(contact_id)
```

### Data Anonymization

Anonymize personal data while preserving business insights:

```python
from core.privacy import privacy_manager
result = privacy_manager.anonymize_personal_data(contact_id)
```

## Security Best Practices

### For Developers

1. **Input Validation**: Always validate and sanitize user input
2. **Parameterized Queries**: Use Django ORM to prevent SQL injection
3. **Secure File Handling**: Use the provided file security utilities
4. **Error Handling**: Don't expose sensitive information in error messages
5. **Logging**: Log security events appropriately
6. **Dependencies**: Keep dependencies updated

### For Deployment

1. **HTTPS Only**: Always use HTTPS in production
2. **Security Headers**: Ensure all security headers are configured
3. **Database Security**: Use strong database credentials and encryption
4. **File Permissions**: Set appropriate file system permissions
5. **Firewall**: Configure firewall rules appropriately
6. **Monitoring**: Set up security monitoring and alerting

### For Operations

1. **Regular Audits**: Run security audits regularly
2. **Log Monitoring**: Monitor security logs for suspicious activity
3. **Data Cleanup**: Regular cleanup of expired data
4. **Backup Security**: Secure backup storage and access
5. **Incident Response**: Have an incident response plan

## Compliance

### GDPR Compliance

The system provides tools for GDPR compliance:

- **Right to Access**: Data export functionality
- **Right to Rectification**: Data update capabilities
- **Right to Erasure**: Data deletion functionality
- **Right to Portability**: Complete data export
- **Data Minimization**: Retention policies and cleanup
- **Privacy by Design**: Security built into the architecture

### Data Retention

Default retention periods:

- Sessions: 90 days
- Conversations: 1 year
- Messages: 1 year
- Audio transcriptions: 6 months
- Knowledge base documents: 3 years
- Audit logs: 7 years

## Incident Response

### Security Incident Procedure

1. **Detection**: Monitor logs and alerts
2. **Assessment**: Determine severity and scope
3. **Containment**: Isolate affected systems
4. **Investigation**: Analyze the incident
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Update security measures

### Contact Information

For security issues:
- Create an issue in the project repository
- Mark as security-sensitive
- Include detailed information about the vulnerability

## Security Updates

- Keep Django and dependencies updated
- Monitor security advisories
- Apply security patches promptly
- Test security updates in staging environment

## Testing Security

### Automated Testing

Run security tests:

```bash
python manage.py test core.tests.test_security
python manage.py test messaging.tests.test_security
```

### Manual Testing

- Test file upload restrictions
- Verify rate limiting
- Check input sanitization
- Validate security headers
- Test authentication flows

## Troubleshooting

### Common Issues

1. **Rate Limiting False Positives**: Adjust rate limits in settings
2. **File Upload Failures**: Check file type and size restrictions
3. **CSP Violations**: Update CSP rules for new resources
4. **Session Timeouts**: Adjust session timeout settings

### Debug Mode

Never run with `DEBUG=True` in production. This exposes sensitive information and disables security features.

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [Security Headers Reference](https://securityheaders.com/)
