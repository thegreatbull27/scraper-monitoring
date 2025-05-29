"""
Health check functionality for scrapers.
"""
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from typing import Dict, Any, Callable, List
from urllib.parse import urlparse

from .config import MonitoringConfig


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheck:
    """Individual health check."""
    
    def __init__(self, name: str, check_func: Callable[[], bool], 
                 description: str = "", timeout: float = 5.0):
        self.name = name
        self.check_func = check_func
        self.description = description
        self.timeout = timeout
        self.last_check_time = None
        self.last_status = None
        self.last_error = None
    
    def run(self) -> Dict[str, Any]:
        """Run the health check."""
        start_time = time.time()
        try:
            result = self.check_func()
            status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            error = None
        except Exception as e:
            result = False
            status = HealthStatus.UNHEALTHY
            error = str(e)
        
        duration = time.time() - start_time
        self.last_check_time = time.time()
        self.last_status = status
        self.last_error = error
        
        return {
            "name": self.name,
            "status": status,
            "description": self.description,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": self.last_check_time,
            "error": error
        }


class HealthChecker:
    """Health checker for scrapers."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.checks: List[HealthCheck] = []
        self.server = None
        self.server_thread = None
        self._setup_default_checks()
        
        if self.config.health_check_enabled:
            self.start_server()
    
    def _setup_default_checks(self):
        """Setup default health checks."""
        # Basic system health checks
        self.add_check("cpu_usage", self._check_cpu_usage, 
                      "Check if CPU usage is below 90%")
        self.add_check("memory_usage", self._check_memory_usage, 
                      "Check if memory usage is below 90%")
        self.add_check("disk_space", self._check_disk_space, 
                      "Check if disk space is available")
    
    def _check_cpu_usage(self) -> bool:
        """Check CPU usage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1) < 90.0
        except ImportError:
            return True  # If psutil not available, assume OK
    
    def _check_memory_usage(self) -> bool:
        """Check memory usage."""
        try:
            import psutil
            return psutil.virtual_memory().percent < 90.0
        except ImportError:
            return True
    
    def _check_disk_space(self) -> bool:
        """Check disk space."""
        try:
            import psutil
            return psutil.disk_usage('/').percent < 95.0
        except ImportError:
            return True
    
    def add_check(self, name: str, check_func: Callable[[], bool], 
                  description: str = "", timeout: float = 5.0):
        """Add a health check."""
        health_check = HealthCheck(name, check_func, description, timeout)
        self.checks.append(health_check)
    
    def remove_check(self, name: str):
        """Remove a health check by name."""
        self.checks = [check for check in self.checks if check.name != name]
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = []
        overall_status = HealthStatus.HEALTHY
        
        for check in self.checks:
            result = check.run()
            results.append(result)
            
            if result["status"] == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result["status"] == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "scraper": self.config.scraper_name,
            "version": self.config.scraper_version,
            "environment": self.config.environment,
            "checks": results
        }
    
    def start_server(self):
        """Start the health check HTTP server."""
        if self.server is None:
            try:
                handler = self._create_handler()
                self.server = HTTPServer(('', self.config.health_check_port), handler)
                self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.server_thread.start()
                print(f"Health check server started on port {self.config.health_check_port}")
            except Exception as e:
                print(f"Failed to start health check server: {e}")
    
    def stop_server(self):
        """Stop the health check server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
    
    def _create_handler(self):
        """Create HTTP request handler."""
        health_checker = self
        
        class HealthCheckHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    health_result = health_checker.run_checks()
                    
                    # Set HTTP status based on health
                    if health_result["status"] == HealthStatus.HEALTHY:
                        status_code = 200
                    elif health_result["status"] == HealthStatus.DEGRADED:
                        status_code = 200  # Still OK but degraded
                    else:
                        status_code = 503  # Service unavailable
                    
                    self.send_response(status_code)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(health_result, indent=2).encode())
                    
                elif self.path == '/ready':
                    # Readiness check - simpler version
                    ready_result = {
                        "status": "ready",
                        "timestamp": time.time(),
                        "scraper": health_checker.config.scraper_name
                    }
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(ready_result).encode())
                    
                elif self.path == '/live':
                    # Liveness check - very basic
                    live_result = {
                        "status": "alive",
                        "timestamp": time.time()
                    }
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(live_result).encode())
                    
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress default logging
                pass
        
        return HealthCheckHandler
