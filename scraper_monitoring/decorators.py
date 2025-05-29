"""
Decorators for tracking scraping operations.
"""
import time
import functools
from typing import Optional, Callable, Any
from urllib.parse import urlparse

from .config import MonitoringConfig
from .logger import ScraperLogger
from .metrics import ScraperMetrics


def track_scrape_operation(operation_name: str = "scrape", 
                          item_type: str = "item",
                          logger: Optional[ScraperLogger] = None,
                          metrics: Optional[ScraperMetrics] = None):
    """
    Decorator to track scraping operations with logging and metrics.
    
    Args:
        operation_name: Name of the operation for metrics/logging
        item_type: Type of items being scraped
        logger: ScraperLogger instance
        metrics: ScraperMetrics instance
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            url = kwargs.get('url', '') or (args[1] if len(args) > 1 else '')
            url_domain = urlparse(url).netloc if url else 'unknown'
            
            # Log operation start
            if logger:
                logger.log_scrape_start(url, operation_name)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Determine item count
                items_count = 0
                if isinstance(result, (list, tuple)):
                    items_count = len(result)
                elif isinstance(result, dict) and 'items' in result:
                    items_count = len(result['items'])
                elif result is not None:
                    items_count = 1
                
                # Log success
                if logger:
                    logger.log_scrape_success(url, items_count, operation_name)
                
                # Record metrics
                if metrics:
                    metrics.record_scrape_request(operation_name, "success", url_domain)
                    metrics.record_scrape_duration(operation_name, url_domain, duration)
                    if items_count > 0:
                        metrics.record_items_scraped(operation_name, item_type, items_count)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                
                # Log error
                if logger:
                    logger.log_scrape_error(url, error_msg, operation_name)
                
                # Record metrics
                if metrics:
                    metrics.record_scrape_request(operation_name, "failed", url_domain)
                    metrics.record_scrape_duration(operation_name, url_domain, duration)
                    metrics.record_error(type(e).__name__, operation_name)
                
                raise
        
        return wrapper
    return decorator


def track_page_scrape(logger: Optional[ScraperLogger] = None,
                     metrics: Optional[ScraperMetrics] = None):
    """
    Decorator to track individual page scraping with HTTP metrics.
    
    Args:
        logger: ScraperLogger instance
        metrics: ScraperMetrics instance
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            url = kwargs.get('url', '') or (args[1] if len(args) > 1 else '')
            url_domain = urlparse(url).netloc if url else 'unknown'
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Try to extract status code from result or response
                status_code = "200"  # Default
                if hasattr(result, 'status_code'):
                    status_code = str(result.status_code)
                elif isinstance(result, dict) and 'status_code' in result:
                    status_code = str(result['status_code'])
                
                # Log page load
                if logger:
                    logger.log_page_load(url, duration, int(status_code))
                
                # Record metrics
                if metrics:
                    metrics.record_http_request("GET", status_code, url_domain)
                    metrics.record_http_response_time("GET", url_domain, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record failed HTTP request
                if metrics:
                    metrics.record_http_request("GET", "500", url_domain)
                    metrics.record_http_response_time("GET", url_domain, duration)
                    metrics.record_error(type(e).__name__, "page_scrape")
                
                raise
        
        return wrapper
    return decorator


def track_rate_limit(delay_seconds: float,
                    logger: Optional[ScraperLogger] = None,
                    metrics: Optional[ScraperMetrics] = None):
    """
    Decorator to track rate limiting delays.
    
    Args:
        delay_seconds: Number of seconds to delay
        logger: ScraperLogger instance
        metrics: ScraperMetrics instance
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            url = kwargs.get('url', '') or (args[1] if len(args) > 1 else '')
            url_domain = urlparse(url).netloc if url else 'unknown'
            
            # Log and record rate limit
            if logger:
                logger.log_rate_limit(url, delay_seconds)
            
            if metrics:
                metrics.record_rate_limit(url_domain, delay_seconds)
            
            # Apply delay
            time.sleep(delay_seconds)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_error_handling(error_types: tuple = (Exception,),
                       logger: Optional[ScraperLogger] = None,
                       metrics: Optional[ScraperMetrics] = None,
                       reraise: bool = True):
    """
    Decorator to handle and log errors consistently.
    
    Args:
        error_types: Tuple of exception types to catch
        logger: ScraperLogger instance
        metrics: ScraperMetrics instance
        reraise: Whether to re-raise the exception after logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                operation_name = func.__name__
                
                if logger:
                    logger.error(
                        f"Error in {operation_name}",
                        error=str(e),
                        error_type=type(e).__name__,
                        function=operation_name
                    )
                
                if metrics:
                    metrics.record_error(type(e).__name__, operation_name)
                
                if reraise:
                    raise
                return None
        
        return wrapper
    return decorator
