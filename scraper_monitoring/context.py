"""
Context manager for scraping operations.
"""
import time
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
from urllib.parse import urlparse

from .config import MonitoringConfig
from .logger import ScraperLogger
from .metrics import ScraperMetrics
from .health import HealthChecker


class ScrapingContext:
    """
    Central context manager for scraping operations.
    Provides integrated logging, metrics, and health checking.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.logger = ScraperLogger(self.config)
        self.metrics = ScraperMetrics(self.config)
        self.health_checker = HealthChecker(self.config)
        
        # Start system metrics collection
        self.metrics.start_system_metrics_collection()
        
        # Log initialization
        self.logger.info("Scraping context initialized", 
                        scraper=self.config.scraper_name,
                        version=self.config.scraper_version)
    
    def get_logger(self, component: Optional[str] = None) -> ScraperLogger:
        """Get logger with optional component context."""
        if component:
            return self.logger.bind(component=component)
        return self.logger
    
    def get_metrics(self) -> ScraperMetrics:
        """Get metrics collector."""
        return self.metrics
    
    def get_health_checker(self) -> HealthChecker:
        """Get health checker."""
        return self.health_checker
    
    @contextmanager
    def scrape_operation(self, operation_name: str, url: str = "", 
                        item_type: str = "item", **context):
        """
        Context manager for tracking scraping operations.
        
        Args:
            operation_name: Name of the operation
            url: URL being scraped
            item_type: Type of items being scraped
            **context: Additional context for logging
        """
        start_time = time.time()
        url_domain = urlparse(url).netloc if url else 'unknown'
        
        # Create operation logger with context
        op_logger = self.logger.bind(
            operation=operation_name,
            url=url,
            url_domain=url_domain,
            **context
        )
        
        op_logger.info("Scraping operation started")
        
        try:
            yield {
                'logger': op_logger,
                'metrics': self.metrics,
                'start_time': start_time
            }
            
            duration = time.time() - start_time
            op_logger.info("Scraping operation completed successfully", 
                          duration_seconds=duration)
            
            # Record success metrics
            self.metrics.record_scrape_request(operation_name, "success", url_domain)
            self.metrics.record_scrape_duration(operation_name, url_domain, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            op_logger.error("Scraping operation failed",
                           error=error_msg,
                           error_type=type(e).__name__,
                           duration_seconds=duration)
            
            # Record failure metrics
            self.metrics.record_scrape_request(operation_name, "failed", url_domain)
            self.metrics.record_scrape_duration(operation_name, url_domain, duration)
            self.metrics.record_error(type(e).__name__, operation_name)
            
            raise
    
    @contextmanager
    def page_request(self, url: str, method: str = "GET", **context):
        """
        Context manager for tracking individual page requests.
        
        Args:
            url: URL being requested
            method: HTTP method
            **context: Additional context
        """
        start_time = time.time()
        url_domain = urlparse(url).netloc if url else 'unknown'
        
        req_logger = self.logger.bind(
            url=url,
            url_domain=url_domain,
            method=method,
            **context
        )
        
        req_logger.debug("HTTP request started")
        
        try:
            yield {
                'logger': req_logger,
                'start_time': start_time
            }
            
            duration = time.time() - start_time
            # Default success - actual status should be logged by caller
            self.metrics.record_http_request(method, "200", url_domain)
            self.metrics.record_http_response_time(method, url_domain, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            
            req_logger.error("HTTP request failed",
                           error=str(e),
                           error_type=type(e).__name__,
                           duration_seconds=duration)
            
            self.metrics.record_http_request(method, "500", url_domain)
            self.metrics.record_http_response_time(method, url_domain, duration)
            self.metrics.record_error(type(e).__name__, "http_request")
            
            raise
    
    def record_items_scraped(self, operation: str, item_type: str, count: int):
        """Record items scraped."""
        self.metrics.record_items_scraped(operation, item_type, count)
        self.logger.info(f"Items scraped", 
                        operation=operation,
                        item_type=item_type,
                        count=count)
    
    def record_rate_limit(self, url: str, delay: float):
        """Record rate limiting event."""
        url_domain = urlparse(url).netloc if url else 'unknown'
        self.metrics.record_rate_limit(url_domain, delay)
        self.logger.log_rate_limit(url, delay)
    
    def record_proxy_rotation(self, old_proxy: str, new_proxy: str, reason: str = "rotation"):
        """Record proxy rotation."""
        self.metrics.record_proxy_rotation(reason)
        self.logger.log_proxy_rotation(old_proxy, new_proxy, reason=reason)
    
    def update_queue_size(self, queue_type: str, size: int):
        """Update queue size metric."""
        self.metrics.update_queue_size(queue_type, size)
    
    def add_health_check(self, name: str, check_func, description: str = ""):
        """Add custom health check."""
        self.health_checker.add_check(name, check_func, description)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return self.health_checker.run_checks()
    
    def shutdown(self):
        """Shutdown monitoring services."""
        self.logger.info("Shutting down scraping context")
        self.health_checker.stop_server()
        
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            self.logger.error("Scraping context exiting with error",
                             error_type=exc_type.__name__,
                             error=str(exc_val))
        else:
            self.logger.info("Scraping context completed successfully")
        
        self.shutdown()
