"""
Structured logging with JSON formatting for Grafana/Loki integration.
"""
import logging
import structlog
import sys
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger

from .config import MonitoringConfig


class ScraperLogger:
    """Structured logger for scrapers with Grafana/Loki integration."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured logging with JSON formatting."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, self.config.log_level.upper())
        )
        
        # Setup file handler if specified
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            if self.config.log_format == "json":
                formatter = jsonlogger.JsonFormatter(
                    '%(asctime)s %(name)s %(levelname)s %(message)s'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
        
        # Create bound logger with base context
        self._logger = structlog.get_logger(self.config.scraper_name)
        self._logger = self._logger.bind(**self.config.get_base_labels())
    
    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """Get a bound logger with optional additional context."""
        if name:
            return self._logger.bind(component=name)
        return self._logger
    
    def bind(self, **kwargs) -> structlog.BoundLogger:
        """Bind additional context to the logger."""
        return self._logger.bind(**kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, **kwargs)
    
    def log_scrape_start(self, url: str, operation: str = "scrape", **kwargs):
        """Log the start of a scraping operation."""
        self._logger.info(
            "Scraping operation started",
            operation=operation,
            url=url,
            status="started",
            **kwargs
        )
    
    def log_scrape_success(self, url: str, items_count: int = 0, 
                          operation: str = "scrape", **kwargs):
        """Log successful scraping operation."""
        self._logger.info(
            "Scraping operation completed successfully",
            operation=operation,
            url=url,
            status="success",
            items_scraped=items_count,
            **kwargs
        )
    
    def log_scrape_error(self, url: str, error: str, 
                        operation: str = "scrape", **kwargs):
        """Log failed scraping operation."""
        self._logger.error(
            "Scraping operation failed",
            operation=operation,
            url=url,
            status="failed",
            error=error,
            **kwargs
        )
    
    def log_page_load(self, url: str, response_time: float, 
                     status_code: int, **kwargs):
        """Log page load metrics."""
        self._logger.info(
            "Page loaded",
            url=url,
            response_time_ms=response_time * 1000,
            status_code=status_code,
            **kwargs
        )
    
    def log_rate_limit(self, url: str, delay: float, **kwargs):
        """Log rate limiting events."""
        self._logger.warning(
            "Rate limit applied",
            url=url,
            delay_seconds=delay,
            **kwargs
        )
    
    def log_proxy_rotation(self, old_proxy: str, new_proxy: str, **kwargs):
        """Log proxy rotation events."""
        self._logger.info(
            "Proxy rotated",
            old_proxy=old_proxy,
            new_proxy=new_proxy,
            **kwargs
        )

# Global convenience function
_default_logger = None

def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a logger instance. If no default logger is configured, 
    create one with default configuration.
    """
    global _default_logger
    
    if _default_logger is None:
        from .config import MonitoringConfig
        config = MonitoringConfig()
        _default_logger = ScraperLogger(config)
    
    if name:
        return _default_logger.get_logger(name)
    return _default_logger.get_logger()
