# Scraper Monitoring Library

A centralized Python monitoring library for web scrapers that integrates with your existing Grafana/Loki/Prometheus monitoring stack.

## Features

- **Structured Logging**: JSON-formatted logs that integrate seamlessly with Grafana/Loki
- **Prometheus Metrics**: Comprehensive metrics collection for scraping operations
- **Health Checks**: Built-in health endpoints for monitoring scraper status
- **Context Management**: Easy-to-use context managers for tracking operations
- **Scrapy Integration**: Built-in support for Scrapy spiders
- **Configurable**: Centralized configuration that can be overridden via environment variables

## Installation

```bash
cd /path/to/shared-monitoring
pip install -e .
```

## Quick Start

### Basic Usage

```python
from scraper_monitoring import ScrapingContext, MonitoringConfig

# Configure monitoring
config = MonitoringConfig(
    scraper_name="my_scraper",
    scraper_version="1.0.0",
    environment="production"
)

# Use context manager for automatic monitoring
with ScrapingContext(config) as ctx:
    logger = ctx.get_logger()
    
    # Track a scraping operation
    with ctx.scrape_operation("product_scrape", "https://example.com/products"):
        # Your scraping code here
        products = scrape_products()
        ctx.record_items_scraped("product_scrape", "product", len(products))
```

### Scrapy Integration

```python
# settings.py
EXTENSIONS = {
    'scraper_monitoring.scrapy_integration.ScrapyMonitoringExtension': 100,
}

PROMETHEUS_PORT = 8000
HEALTH_CHECK_PORT = 8001
```

```python
# spider.py
from scraper_monitoring.scrapy_integration import MonitoredSpider

class MySpider(MonitoredSpider):
    name = 'my_spider'
    start_urls = ['https://example.com']
    
    def parse(self, response):
        with self.context.scrape_operation("parse_page", response.url):
            # Your parsing logic
            for item in self.extract_items(response):
                yield item
```

### Decorators

```python
from scraper_monitoring import track_scrape_operation, track_page_scrape

@track_scrape_operation(operation_name="product_scrape", item_type="product")
def scrape_products(url):
    # Your scraping logic
    return products

@track_page_scrape()
def fetch_page(url):
    # Your page fetching logic
    return response
```

## Configuration

### Environment Variables

All configuration options can be overridden using environment variables:

- `LOKI_URL`: Loki endpoint (default: http://localhost:3100)
- `GRAFANA_URL`: Grafana endpoint (default: http://localhost:3000)
- `PROMETHEUS_URL`: Prometheus endpoint (default: http://localhost:9090)
- `PROMETHEUS_PORT`: Port for exposing metrics (default: 8000)
- `HEALTH_CHECK_PORT`: Port for health checks (default: 8001)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FORMAT`: Log format - json or standard (default: json)
- `LOG_FILE`: Log file path (optional)
- `SCRAPER_NAME`: Name of the scraper
- `SCRAPER_VERSION`: Version of the scraper
- `ENVIRONMENT`: Environment (development, staging, production)

### Configuration Object

```python
from scraper_monitoring import MonitoringConfig

config = MonitoringConfig(
    scraper_name="my_scraper",
    scraper_version="1.0.0",
    environment="production",
    log_level="INFO",
    prometheus_port=8000,
    health_check_port=8001,
    custom_labels={"team": "data", "project": "scraping"}
)
```

## Metrics

The library automatically collects the following Prometheus metrics:

### Scraping Metrics
- `scraper_requests_total`: Total scraping requests
- `scraper_duration_seconds`: Scraping operation duration
- `scraper_items_scraped_total`: Total items scraped
- `scraper_errors_total`: Total errors

### HTTP Metrics
- `scraper_http_requests_total`: Total HTTP requests
- `scraper_http_response_duration_seconds`: HTTP response times

### System Metrics
- `scraper_system_cpu_usage_percent`: CPU usage
- `scraper_system_memory_usage_bytes`: Memory usage

### Rate Limiting Metrics
- `scraper_rate_limit_delays_total`: Rate limit events
- `scraper_rate_limit_delay_seconds`: Rate limit delay duration

## Health Checks

The library provides health check endpoints:

- `GET /health`: Comprehensive health check
- `GET /ready`: Readiness check
- `GET /live`: Liveness check

Health checks include:
- CPU usage monitoring
- Memory usage monitoring
- Disk space monitoring
- Custom health checks

### Custom Health Checks

```python
def check_database_connection():
    # Your database check logic
    return database.is_connected()

ctx.add_health_check("database", check_database_connection, "Database connectivity")
```

## Logging

All logs are structured JSON format by default, making them perfect for Grafana/Loki:

```json
{
  "timestamp": "2023-12-01T10:30:00.000Z",
  "level": "info",
  "scraper_name": "my_scraper",
  "scraper_version": "1.0.0",
  "environment": "production",
  "operation": "product_scrape",
  "url": "https://example.com/products",
  "status": "success",
  "items_scraped": 25,
  "duration_seconds": 2.5
}
```

## Integration with Existing Stack

This library is designed to work with your existing monitoring setup:

1. **Loki**: Structured logs are automatically formatted for Loki ingestion
2. **Prometheus**: Metrics are exposed on the configured port
3. **Grafana**: Create dashboards using the provided metrics and logs

### Example Grafana Queries

```promql
# Scraping success rate
rate(scraper_requests_total{status="success"}[5m]) / rate(scraper_requests_total[5m]) * 100

# Average scraping duration
rate(scraper_duration_seconds_sum[5m]) / rate(scraper_duration_seconds_count[5m])

# Items scraped per minute
rate(scraper_items_scraped_total[1m]) * 60
```

## Docker Integration

```dockerfile
# Dockerfile
FROM python:3.9

# Install monitoring library
COPY shared-monitoring /app/shared-monitoring
RUN pip install -e /app/shared-monitoring

# Your scraper code
COPY . /app
WORKDIR /app

# Expose metrics and health check ports
EXPOSE 8000 8001

CMD ["python", "your_scraper.py"]
```

## Examples

See the `examples/` directory for complete working examples of:
- Basic scraper with monitoring
- Scrapy spider integration
- Custom metrics and health checks
- Docker deployment

## Contributing

1. Install development dependencies: `pip install -e .[dev]`
2. Run tests: `pytest`
3. Check code style: `flake8`
4. Update documentation as needed
