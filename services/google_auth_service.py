import os
import pickle
import logging
import time
import warnings
from typing import Dict, Optional, Any
from pathlib import Path
from logging.handlers import RotatingFileHandler

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient import errors as google_errors
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    warnings.warn(
        "Google API libraries not found. Please install required packages:\n"
        "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )

from config.google_config import GOOGLE_SERVICE_CONFIGS, SERVICE_RETRY_CONFIG



# Define exceptions first
class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class ServiceInitializationError(Exception):
    """Raised when service initialization fails."""
    pass

class GoogleAPIError(Exception):
    """Base exception for Google API errors"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        super().__init__(message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {super().__str__()}"
        return super().__str__()

class QuotaExceededError(GoogleAPIError):
    """Raised when API quota is exceeded"""
    pass

class PermissionError(GoogleAPIError):
    """Raised when permission is denied"""
    pass

class GoogleAuthService:
    """Centralized authentication service for Google API services."""
    
    def __init__(self, credentials_file: str, token_file: str, scopes: list):
        if not GOOGLE_APIS_AVAILABLE:
            self.logger = logging.getLogger(__name__)
            self.logger.error("Google API libraries are not installed")
            raise ImportError("Google API libraries are not installed. Please install required packages.")
            
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.creds: Optional[Credentials] = None
        self.services: Dict = {}
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self._setup_token_directory()
        
    def _setup_logging(self):
        """Configure logging with rotation"""
        if not self.logger.handlers:
            log_file = 'logs/google_auth.log'
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handler = RotatingFileHandler(
                log_file, 
                maxBytes=1024*1024,  # 1MB
                backupCount=5
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def authenticate(self) -> Credentials:
        """Handle OAuth2 authentication flow with improved error handling."""
        try:
            self.logger.info("Starting authentication process")
            if os.path.exists(self.token_file):
                self.logger.debug(f"Loading existing token from {self.token_file}")
                try:
                    with open(self.token_file, 'rb') as token:
                        self.creds = pickle.load(token)
                except (pickle.UnpicklingError, EOFError) as e:
                    self.logger.warning(f"Token file corrupted, removing: {str(e)}")
                    os.remove(self.token_file)
                    self.creds = None
                    
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.logger.info("Refreshing expired credentials")
                    try:
                        self.creds.refresh(Request())
                    except Exception as e:
                        self.logger.error(f"Token refresh failed: {str(e)}")
                        self.creds = None
                
                if not self.creds:
                    self.logger.info("Initiating new authentication flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    self.creds = flow.run_local_server(port=0)
                    
                self.logger.debug(f"Saving new token to {self.token_file}")
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
                    
            self.logger.info("Authentication successful")
            return self.creds
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate: {str(e)}")
    
    def initialize_services(self) -> Dict:
        """Initialize all required Google API services with retry logic."""
        try:
            self.logger.info("Initializing Google services")
            if not self.creds:
                self.authenticate()
                
            for service_name, config in GOOGLE_SERVICE_CONFIGS.items():
                if not self._validate_service_config(service_name):
                    raise ServiceInitializationError(f"Invalid configuration for {service_name}")
                    
                self.logger.debug(f"Initializing {service_name} service")
                api_name, version = config['api_info']
                retries = SERVICE_RETRY_CONFIG['max_retries']
                delay = SERVICE_RETRY_CONFIG['base_delay']
                
                while retries > 0:
                    try:
                        self.services[service_name] = build(
                            api_name, 
                            version, 
                            credentials=self.creds,
                            cache_discovery=False
                        )
                        
                        # Validate the service after initialization
                        if not self.validate_service(service_name):
                            raise ServiceInitializationError(f"Service {service_name} validation failed")
                            
                        break
                        
                    except (google_errors.Error, ServiceInitializationError) as e:
                        retries -= 1
                        if retries == 0:
                            self._handle_google_error(e, service_name)
                        
                        self.logger.warning(
                            f"Retry {SERVICE_RETRY_CONFIG['max_retries'] - retries} "
                            f"initializing {service_name} service: {str(e)}"
                        )
                        
                        if SERVICE_RETRY_CONFIG['exponential_backoff']:
                            delay *= 2
                        time.sleep(min(delay, SERVICE_RETRY_CONFIG['max_delay']))
                
            self.logger.info("All services initialized successfully")
            return self.services
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {str(e)}")
            raise ServiceInitializationError(f"Failed to initialize services: {str(e)}")
    
    def get_service(self, service_name: str):
        """Get a specific Google service client with validation."""
        try:
            if service_name not in GOOGLE_SERVICE_CONFIGS:
                raise ValueError(f"Invalid service name: {service_name}")
                
            if service_name not in self.services:
                self.logger.debug(f"Service {service_name} not initialized, initializing now")
                self.initialize_services()
                
            service = self.services.get(service_name)
            if not service:
                raise ServiceInitializationError(f"Service {service_name} initialization failed")
                
            return service
            
        except Exception as e:
            self.logger.error(f"Failed to get service {service_name}: {str(e)}")
            raise ServiceInitializationError(f"Failed to get service {service_name}: {str(e)}")
    
    def _setup_token_directory(self) -> None:
        """Ensure token directory exists"""
        token_dir = os.path.dirname(self.token_file)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
    
    def validate_service(self, service_name: str) -> bool:
        """Validate if a service is properly initialized and responsive"""
        try:
            service = self.get_service(service_name)
            # Use minimal API calls to test service
            if service_name == 'drive':
                service.files().list(pageSize=1, fields="files(id, name)").execute()
            elif service_name == 'docs':
                # Just check if service is initialized
                if not hasattr(service, 'documents'):
                    raise google_errors.Error("Documents API not initialized properly")
            elif service_name == 'sheets':
                # Just check if service is initialized
                if not hasattr(service, 'spreadsheets'):
                    raise google_errors.Error("Sheets API not initialized properly")
            elif service_name == 'calendar':
                service.calendarList().list(maxResults=1).execute()
            
            self.logger.info(f"Service {service_name} validated successfully")
            return True
            
        except google_errors.Error as e:
            self.logger.error(f"Service validation error for {service_name}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating {service_name}: {str(e)}")
            return False
    
    def _handle_google_error(self, error: google_errors.Error, service_name: str) -> None:
        """Handle specific Google API errors with context"""
        error_msg = str(error)
        if isinstance(error, google_errors.HttpError):
            if error.resp.status == 403:
                if 'quotaExceeded' in error_msg:
                    self.logger.error(f"Quota exceeded for {service_name} service")
                    raise QuotaExceededError(f"API quota exceeded for {service_name}")
                self.logger.error(f"Permission denied for {service_name} service")
                raise PermissionError(f"Permission denied for {service_name}")
            elif error.resp.status == 429:
                self.logger.warning(f"Rate limit hit for {service_name} service")
                raise QuotaExceededError(f"Rate limit exceeded for {service_name}")
        self.logger.error(f"Google API error in {service_name}: {error_msg}")
        raise GoogleAPIError(f"Error in {service_name}: {error_msg}")
    
    def _validate_service_config(self, service_name: str) -> bool:
        """Validate service configuration before initialization."""
        try:
            if service_name not in GOOGLE_SERVICE_CONFIGS:
                self.logger.error(f"Invalid service name: {service_name}")
                return False
                
            config = GOOGLE_SERVICE_CONFIGS[service_name]
            required_fields = ['api_info', 'dependencies', 'required_scopes']
            
            if not all(field in config for field in required_fields):
                self.logger.error(f"Missing required configuration fields for {service_name}")
                return False
                
            # Validate dependencies
            for dependency in config['dependencies']:
                if dependency not in GOOGLE_SERVICE_CONFIGS:
                    self.logger.error(f"Invalid dependency {dependency} for {service_name}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed for {service_name}: {str(e)}")
            return False