"""
Scraper Monitoring Library

A centralized monitoring helper library that provides:
- Structured logging with JSON formatting for Grafana/Loki
- Prometheus metrics collection and exposure
- Health check endpoints
- Configuration management for monitoring services
- Context managers for tracking scraping operations
"""

from .config import MonitoringConfig
from .logger import ScraperLogger, get_logger
from .metrics import ScraperMetrics, get_metrics_registry
from .health import HealthChecker, start_health_server
from .decorators import track_scrape_operation, track_page_scrape, track_scraping_operation
from .context import ScrapingContext, MonitoringContext, monitor_operation

__version__ = "1.0.0"
__all__ = [
    "MonitoringConfig",
    "ScraperLogger", 
    "get_logger",
    "ScraperMetrics",
    "get_metrics_registry",
    "HealthChecker",
    "start_health_server",
    "track_scrape_operation",
    "track_page_scrape",
    "track_scraping_operation",
    "ScrapingContext",
    "MonitoringContext",
    "monitor_operation",
]
