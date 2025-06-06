"""
Prometheus metrics collection for scrapers.
"""
import time
import threading
from typing import Dict, Optional, List
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, start_http_server
from prometheus_client.core import CollectorRegistry
import psutil

from .config import MonitoringConfig


class ScraperMetrics:
    """Prometheus metrics collector for scrapers."""
    
    def __init__(self, config: MonitoringConfig, registry: Optional[CollectorRegistry] = None):
        self.config = config
        self.registry = registry or CollectorRegistry()
        self._server_started = False
        self._server_thread = None
        
        # Base labels for all metrics
        self.base_labels = list(self.config.get_base_labels().keys())
        self.base_label_values = list(self.config.get_base_labels().values())
        
        self._setup_metrics()
        
        if self.config.prometheus_enabled:
            self.start_metrics_server()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        # Scraping operation metrics
        self.scrape_requests_total = Counter(
            'scraper_requests_total',
            'Total number of scraping requests',
            labelnames=self.base_labels + ['operation', 'status', 'url_domain'],
            registry=self.registry
        )
        
        self.scrape_duration_seconds = Histogram(
            'scraper_duration_seconds',
            'Time spent on scraping operations',
            labelnames=self.base_labels + ['operation', 'url_domain'],
            registry=self.registry
        )
        
        self.items_scraped_total = Counter(
            'scraper_items_scraped_total',
            'Total number of items scraped',
            labelnames=self.base_labels + ['operation', 'item_type'],
            registry=self.registry
        )
        
        # HTTP response metrics
        self.http_requests_total = Counter(
            'scraper_http_requests_total',
            'Total HTTP requests made',
            labelnames=self.base_labels + ['method', 'status_code', 'url_domain'],
            registry=self.registry
        )
        
        self.http_response_duration_seconds = Histogram(
            'scraper_http_response_duration_seconds',
            'HTTP response time',
            labelnames=self.base_labels + ['method', 'url_domain'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'scraper_errors_total',
            'Total number of errors',
            labelnames=self.base_labels + ['error_type', 'operation'],
            registry=self.registry
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'scraper_system_cpu_usage_percent',
            'System CPU usage percentage',
            labelnames=self.base_labels,
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'scraper_system_memory_usage_bytes',
            'System memory usage in bytes',
            labelnames=self.base_labels,
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limit_delays_total = Counter(
            'scraper_rate_limit_delays_total',
            'Total number of rate limit delays',
            labelnames=self.base_labels + ['url_domain'],
            registry=self.registry
        )
        
        self.rate_limit_delay_seconds = Histogram(
            'scraper_rate_limit_delay_seconds',
            'Duration of rate limit delays',
            labelnames=self.base_labels + ['url_domain'],
            registry=self.registry
        )
        
        # Proxy metrics
        self.proxy_rotations_total = Counter(
            'scraper_proxy_rotations_total',
            'Total number of proxy rotations',
            labelnames=self.base_labels + ['reason'],
            registry=self.registry
        )
        
        # Queue metrics (for scrapy or other queue-based scrapers)
        self.queue_size = Gauge(
            'scraper_queue_size',
            'Current size of the scraping queue',
            labelnames=self.base_labels + ['queue_type'],
            registry=self.registry
        )
    
    def start_metrics_server(self):
        """Start Prometheus metrics server."""
        if not self._server_started and self.config.prometheus_enabled:
            try:
                start_http_server(self.config.prometheus_port, registry=self.registry)
                self._server_started = True
                print(f"Prometheus metrics server started on port {self.config.prometheus_port}")
            except Exception as e:
                print(f"Failed to start metrics server: {e}")
    
    def _get_labels_dict(self, additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get combined labels dictionary."""
        labels = self.config.get_base_labels().copy()
        if additional_labels:
            labels.update(additional_labels)
        return labels
    
    def record_scrape_request(self, operation: str, status: str, url_domain: str):
        """Record a scraping request."""
        labels = self._get_labels_dict({
            'operation': operation,
            'status': status,
            'url_domain': url_domain
        })
        self.scrape_requests_total.labels(**labels).inc()
    
    def record_scrape_duration(self, operation: str, url_domain: str, duration: float):
        """Record scraping operation duration."""
        labels = self._get_labels_dict({
            'operation': operation,
            'url_domain': url_domain
        })
        self.scrape_duration_seconds.labels(**labels).observe(duration)
    
    def record_items_scraped(self, operation: str, item_type: str, count: int = 1):
        """Record number of items scraped."""
        labels = self._get_labels_dict({
            'operation': operation,
            'item_type': item_type
        })
        self.items_scraped_total.labels(**labels).inc(count)
    
    def record_http_request(self, method: str, status_code: str, url_domain: str):
        """Record HTTP request."""
        labels = self._get_labels_dict({
            'method': method,
            'status_code': status_code,
            'url_domain': url_domain
        })
        self.http_requests_total.labels(**labels).inc()
    
    def record_http_response_time(self, method: str, url_domain: str, duration: float):
        """Record HTTP response time."""
        labels = self._get_labels_dict({
            'method': method,
            'url_domain': url_domain
        })
        self.http_response_duration_seconds.labels(**labels).observe(duration)
    
    def record_error(self, error_type: str, operation: str):
        """Record an error."""
        labels = self._get_labels_dict({
            'error_type': error_type,
            'operation': operation
        })
        self.errors_total.labels(**labels).inc()
    
    def record_rate_limit(self, url_domain: str, delay: float):
        """Record rate limiting event."""
        labels_count = self._get_labels_dict({'url_domain': url_domain})
        labels_delay = self._get_labels_dict({'url_domain': url_domain})
        
        self.rate_limit_delays_total.labels(**labels_count).inc()
        self.rate_limit_delay_seconds.labels(**labels_delay).observe(delay)
    
    def record_proxy_rotation(self, reason: str = "rotation"):
        """Record proxy rotation."""
        labels = self._get_labels_dict({'reason': reason})
        self.proxy_rotations_total.labels(**labels).inc()
    
    def update_queue_size(self, queue_type: str, size: int):
        """Update queue size metric."""
        labels = self._get_labels_dict({'queue_type': queue_type})
        self.queue_size.labels(**labels).set(size)
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent()
            labels = self._get_labels_dict()
            self.system_cpu_usage.labels(**labels).set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.labels(**labels).set(memory.used)
        except Exception as e:
            print(f"Failed to update system metrics: {e}")
    
    def start_system_metrics_collection(self, interval: int = 30):
        """Start background thread to collect system metrics."""
        def collect_metrics():
            while True:
                self.update_system_metrics()
                time.sleep(interval)
        
        if not self._server_thread:
            self._server_thread = threading.Thread(target=collect_metrics, daemon=True)
            self._server_thread.start()
    
    def get_registry(self) -> CollectorRegistry:
        """Get the metrics registry."""
        return self.registry

# Global convenience function
_default_metrics = None

def get_metrics_registry() -> CollectorRegistry:
    """
    Get a metrics registry. If no default metrics collector is configured,
    create one with default configuration.
    """
    global _default_metrics
    
    if _default_metrics is None:
        from .config import MonitoringConfig
        config = MonitoringConfig()
        _default_metrics = ScraperMetrics(config)
    
    return _default_metrics.get_registry()
