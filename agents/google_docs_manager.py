from services.google_auth_service import GoogleAuthService, AuthenticationError, ServiceInitializationError
from config.google_config import GOOGLE_API_SCOPES, REQUIRED_SERVICES
from typing import List, Dict, Any
import datetime
import logging

class GoogleDocsManager:
    def __init__(self, auth_service: GoogleAuthService):
        self.logger = logging.getLogger(__name__)
        self.auth_service = auth_service
        self.initialize_services()
        
    def initialize_services(self):
        """Initialize all required Google services with validation."""
        try:
            services = self.auth_service.initialize_services()
            
            # Initialize services
            for service_name in REQUIRED_SERVICES:
                service = services.get(service_name)
                if not service:
                    raise ServiceInitializationError(f"Failed to initialize {service_name} service")
                setattr(self, f"{service_name}_service", service)
                
            self.logger.info("Successfully initialized all Google services")
            if not self.validate_services():
                raise ServiceInitializationError("Service validation failed after initialization")
                
        except Exception as e:
            self.logger.error(f"Service initialization failed: {str(e)}")
            raise ServiceInitializationError(f"Failed to initialize services: {str(e)}")
    
    def validate_services(self) -> bool:
        """Validate that all required services are initialized and accessible."""
        try:
            for service_name in REQUIRED_SERVICES:
                service = getattr(self, f"{service_name}_service", None)
                if not service:
                    self.logger.error(f"Missing required service: {service_name}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Service validation failed: {str(e)}")
            return False

class ServiceInitializationError(Exception):
    """Raised when service initialization fails."""
    pass