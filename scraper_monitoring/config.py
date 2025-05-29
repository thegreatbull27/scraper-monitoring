"""
Configuration management for monitoring services.
Centralizes all monitoring-related configuration in one place.
"""
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class MonitoringConfig:
    """Configuration for monitoring services."""
    
    # Grafana/Loki Configuration
    loki_url: str = "http://localhost:3100"
    grafana_url: str = "http://localhost:3000"
    grafana_username: str = "admin"
    grafana_password: str = "admin"
    
    # Prometheus Configuration
    prometheus_url: str = "http://localhost:9090"
    prometheus_port: int = 8000  # Port for exposing metrics
    prometheus_enabled: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or standard
    log_file: Optional[str] = None
    
    # Scraper Identification
    scraper_name: str = "default_scraper"
    scraper_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    
    # Health Check Configuration
    health_check_enabled: bool = True
    health_check_port: int = 8001
    
    # Custom Labels for Metrics
    custom_labels: Dict[str, str] = None
    
    def __post_init__(self):
        """Initialize default values and environment overrides."""
        if self.custom_labels is None:
            self.custom_labels = {}
            
        # Environment variable overrides
        self.loki_url = os.getenv("LOKI_URL", self.loki_url)
        self.grafana_url = os.getenv("GRAFANA_URL", self.grafana_url)
        self.grafana_username = os.getenv("GRAFANA_USERNAME", self.grafana_username)
        self.grafana_password = os.getenv("GRAFANA_PASSWORD", self.grafana_password)
        self.prometheus_url = os.getenv("PROMETHEUS_URL", self.prometheus_url)
        self.prometheus_port = int(os.getenv("PROMETHEUS_PORT", str(self.prometheus_port)))
        self.prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_format = os.getenv("LOG_FORMAT", self.log_format)
        self.log_file = os.getenv("LOG_FILE", self.log_file)
        self.scraper_name = os.getenv("SCRAPER_NAME", self.scraper_name)
        self.scraper_version = os.getenv("SCRAPER_VERSION", self.scraper_version)
        self.environment = os.getenv("ENVIRONMENT", self.environment)
        self.health_check_enabled = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
        self.health_check_port = int(os.getenv("HEALTH_CHECK_PORT", str(self.health_check_port)))
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MonitoringConfig':
        """Create config from dictionary."""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'loki_url': self.loki_url,
            'grafana_url': self.grafana_url,
            'grafana_username': self.grafana_username,
            'grafana_password': self.grafana_password,
            'prometheus_url': self.prometheus_url,
            'prometheus_port': self.prometheus_port,
            'prometheus_enabled': self.prometheus_enabled,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'log_file': self.log_file,
            'scraper_name': self.scraper_name,
            'scraper_version': self.scraper_version,
            'environment': self.environment,
            'health_check_enabled': self.health_check_enabled,
            'health_check_port': self.health_check_port,
            'custom_labels': self.custom_labels,
        }
    
    def get_base_labels(self) -> Dict[str, str]:
        """Get base labels for metrics and logs."""
        labels = {
            'scraper_name': self.scraper_name,
            'scraper_version': self.scraper_version,
            'environment': self.environment,
        }
        labels.update(self.custom_labels)
        return labels
