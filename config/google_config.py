from pathlib import Path
from typing import Dict, Tuple, List, Union
from enum import Enum
import os

class GoogleScope(Enum):
    """Enum for Google API Scopes with access levels"""
    DRIVE_FILE = ('https://www.googleapis.com/auth/drive.file', 'Per-file access to Google Drive', 'write')
    DOCS_READONLY = ('https://www.googleapis.com/auth/documents.readonly', 'Read-only access to Google Docs', 'read')
    SHEETS_READONLY = ('https://www.googleapis.com/auth/spreadsheets.readonly', 'Read-only access to Google Sheets', 'read')
    SLIDES_READONLY = ('https://www.googleapis.com/auth/presentations.readonly', 'Read-only access to Google Slides', 'read')
    CALENDAR_READONLY = ('https://www.googleapis.com/auth/calendar.readonly', 'Read-only access to Google Calendar', 'read')
    CALENDAR_FULL = ('https://www.googleapis.com/auth/calendar', 'Full access to Google Calendar', 'write')

    def __init__(self, url: str, description: str, access_level: str):
        self.url = url
        self.description = description
        self.access_level = access_level

# Service version management
class GoogleAPIVersion:
    DOCS = 'v1'
    SHEETS = 'v4'
    SLIDES = 'v1'
    DRIVE = 'v3'
    CALENDAR = 'v3'

# Service Configurations with dependency management
GOOGLE_SERVICE_CONFIGS: Dict[str, Dict[str, Union[Tuple[str, str], List[str], Dict[str, str]]]] = {
    'docs': {
        'api_info': ('docs', GoogleAPIVersion.DOCS),
        'dependencies': ['drive'],
        'required_scopes': [GoogleScope.DOCS_READONLY.url],
        'fallback_options': {
            'offline_mode': True,
            'cache_ttl': 3600
        }
    },
    'sheets': {
        'api_info': ('sheets', GoogleAPIVersion.SHEETS),
        'dependencies': ['drive'],
        'required_scopes': [GoogleScope.SHEETS_READONLY.url],
        'fallback_options': {
            'offline_mode': True,
            'cache_ttl': 3600
        }
    },
    'slides': {
        'api_info': ('slides', GoogleAPIVersion.SLIDES),
        'dependencies': ['drive'],
        'required_scopes': [GoogleScope.SLIDES_READONLY.url],
        'fallback_options': {
            'offline_mode': True,
            'cache_ttl': 3600
        }
    },
    'drive': {
        'api_info': ('drive', GoogleAPIVersion.DRIVE),
        'dependencies': [],
        'required_scopes': [GoogleScope.DRIVE_FILE.url],
        'fallback_options': {
            'offline_mode': False,
            'cache_ttl': 1800
        }
    },
    'calendar': {
        'api_info': ('calendar', GoogleAPIVersion.CALENDAR),
        'dependencies': [],
        'required_scopes': [GoogleScope.CALENDAR_FULL.url, GoogleScope.CALENDAR_READONLY.url],
        'fallback_options': {
            'offline_mode': False,
            'cache_ttl': 300
        }
    }
}

# Authentication Settings with enhanced security and validation
AUTH_SETTINGS = {
    'credentials_file': Path(os.getenv('GOOGLE_CREDENTIALS_FILE', 'multiagent_demo_credentials.json')),
    'token_file': Path(os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')),
    'token_dir': Path(os.getenv('GOOGLE_TOKEN_DIR', 'tokens')),
    'scopes_file': Path(os.getenv('GOOGLE_SCOPES_FILE', 'scopes.json')),
    'security': {
        'token_encryption': bool(os.getenv('GOOGLE_TOKEN_ENCRYPTION', True)),
        'encryption_key': os.getenv('GOOGLE_TOKEN_ENCRYPTION_KEY'),
        'token_rotation_days': int(os.getenv('GOOGLE_TOKEN_ROTATION_DAYS', 7)),
        'max_token_age_days': int(os.getenv('GOOGLE_MAX_TOKEN_AGE_DAYS', 30))
    }
}

# Enhanced retry configuration with circuit breaker
SERVICE_RETRY_CONFIG = {
    'max_retries': int(os.getenv('GOOGLE_MAX_RETRIES', 3)),
    'base_delay': float(os.getenv('GOOGLE_BASE_DELAY', 1.0)),
    'max_delay': float(os.getenv('GOOGLE_MAX_DELAY', 10.0)),
    'exponential_backoff': bool(os.getenv('GOOGLE_USE_EXPONENTIAL_BACKOFF', True)),
    'circuit_breaker': {
        'failure_threshold': int(os.getenv('GOOGLE_CIRCUIT_BREAKER_THRESHOLD', 5)),
        'reset_timeout': int(os.getenv('GOOGLE_CIRCUIT_BREAKER_RESET', 300)),
        'half_open_timeout': int(os.getenv('GOOGLE_CIRCUIT_BREAKER_HALF_OPEN', 60))
    },
    'quota_management': {
        'daily_quota': int(os.getenv('GOOGLE_DAILY_QUOTA', 10000)),
        'per_minute_quota': int(os.getenv('GOOGLE_MINUTE_QUOTA', 100)),
        'quota_buffer_percent': float(os.getenv('GOOGLE_QUOTA_BUFFER', 0.1))
    }
}

# Cache configuration
CACHE_CONFIG = {
    'enabled': bool(os.getenv('GOOGLE_CACHE_ENABLED', True)),
    'backend': os.getenv('GOOGLE_CACHE_BACKEND', 'redis'),
    'ttl': int(os.getenv('GOOGLE_CACHE_TTL', 3600)),
    'max_size': int(os.getenv('GOOGLE_CACHE_MAX_SIZE', 1000)),
    'compression': bool(os.getenv('GOOGLE_CACHE_COMPRESSION', True))
}

def validate_service_config(service_name: str) -> bool:
    """Validate service configuration and dependencies."""
    if service_name not in GOOGLE_SERVICE_CONFIGS:
        return False
        
    service_config = GOOGLE_SERVICE_CONFIGS[service_name]
    
    # Check required fields
    required_fields = ['api_info', 'dependencies', 'required_scopes', 'fallback_options']
    if not all(field in service_config for field in required_fields):
        return False
        
    # Validate dependencies
    for dependency in service_config['dependencies']:
        if dependency not in GOOGLE_SERVICE_CONFIGS:
            return False
            
    return True

def get_required_scopes(services: List[str]) -> List[str]:
    """Get all required scopes for given services including dependencies."""
    scopes = set()
    for service in services:
        if service in GOOGLE_SERVICE_CONFIGS:
            scopes.update(GOOGLE_SERVICE_CONFIGS[service]['required_scopes'])
            # Add dependency scopes
            for dependency in GOOGLE_SERVICE_CONFIGS[service]['dependencies']:
                scopes.update(GOOGLE_SERVICE_CONFIGS[dependency]['required_scopes'])
    return list(scopes)
