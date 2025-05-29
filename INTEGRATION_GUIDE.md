# Integrating Shared Monitoring with Your Ruger Scraper

This guide shows you how to integrate the shared monitoring library with your existing Ruger scraper.

## Quick Integration

### Option 1: Minimal Integration (Easiest)

1. **Install the monitoring library:**
```bash
cd /Users/benlokos/development/Scrapers/shared-monitoring
pip install -e .
```

2. **Update your Ruger scraper settings** (`/Users/benlokos/development/Scrapers/ruger_scraper/ruger_scraper/settings.py`):

```python
# Add to the top of settings.py
from scraper_monitoring import MonitoringConfig

# Add monitoring extension
EXTENSIONS = {
    'scraper_monitoring.scrapy_integration.ScrapyMonitoringExtension': 100,
}

# Monitoring configuration
PROMETHEUS_PORT = 8000
HEALTH_CHECK_PORT = 8001
SCRAPER_NAME = 'ruger_scraper'
SCRAPER_VERSION = '2.0.0'
ENVIRONMENT = 'production'  # or 'development'

# Your existing settings...
BOT_NAME = 'ruger_scraper'
# ... rest of your settings
```

3. **That's it!** Your scraper will now automatically:
   - Log structured JSON to `/app/logs/scrapy.log`
   - Expose Prometheus metrics on port 8000
   - Provide health checks on port 8001
   - Track all scraping operations

### Option 2: Enhanced Integration (Recommended)

For more control, create a new monitored version of your spider:

1. **Create a new spider file** (`ruger_scraper_monitored.py`):

```python
import scrapy
from urllib.parse import urljoin
from scraper_monitoring import ScrapingContext, MonitoringConfig

class RugerSpiderMonitored(scrapy.Spider):
    name = 'ruger_spider_monitored'
    start_urls = ['https://ruger.com/products/lcp/models.html']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup monitoring
        config = MonitoringConfig(
            scraper_name="ruger_scraper",
            scraper_version="2.0.0",
            environment="production",
            custom_labels={"manufacturer": "ruger", "product_type": "firearms"}
        )
        self.context = ScrapingContext(config)
        
        # Add custom health check
        self.context.add_health_check(
            "start_urls_reachable",
            self._check_start_urls,
            "Check if start URLs are reachable"
        )
    
    def _check_start_urls(self):
        """Custom health check for start URLs."""
        import requests
        try:
            response = requests.head(self.start_urls[0], timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def parse(self, response):
        """Parse main page - your existing logic with monitoring."""
        with self.context.scrape_operation("discover_categories", response.url) as op:
            op_logger = op['logger']
            
            base_url = response.url
            nav_data_blocks = response.css('div.nav-data[data-cat="all"] ul li.clearfix a::attr(href)').getall()
            
            op_logger.info("Found category links", count=len(nav_data_blocks))
            
            for link in nav_data_blocks:
                if link.startswith('javascript') or not link.strip():
                    continue
                full_link = urljoin(base_url, link)
                yield response.follow(full_link, self.parse_intermediate_page)
            
            # Record categories discovered
            self.context.record_items_scraped("discover_categories", "category", len(nav_data_blocks))

    def parse_intermediate_page(self, response):
        """Parse intermediate page - your existing logic with monitoring."""
        with self.context.scrape_operation("discover_products", response.url) as op:
            op_logger = op['logger']
            
            base_url = response.url
            product_links = response.css('div.product-thumb.handgun.de-overlay a.image-link::attr(href), div.product-thumb.long-gun.de-overlay a.image-link::attr(href)').getall()
            
            op_logger.info("Found product links", count=len(product_links))
            
            for link in product_links:
                full_link = urljoin(base_url, link)
                yield response.follow(full_link, self.parse_product)
            
            self.context.record_items_scraped("discover_products", "product_link", len(product_links))

    def parse_product(self, response):
        """Parse product page - your existing logic with monitoring."""
        with self.context.scrape_operation("extract_product", response.url, item_type="product") as op:
            op_logger = op['logger']
            
            try:
                # Your existing extraction logic
                product_name = ''.join(response.css('div.content.title h1 *::text').getall()).strip()
                specs_section = response.css('div.content.specs')
                details = {}

                for spec_group in specs_section.css('ul.big-specs, ul.small-specs'):
                    for spec in spec_group.css('li'):
                        key = spec.css('em::text, ::text').extract_first().strip(': ')
                        value = spec.css('span::text').extract_first(default='').strip()
                        details[key] = value

                features = [feature.strip() for feature in specs_section.css('ul.features li p::text').getall()]

                # Your existing yield logic
                product = {
                    'product_name': product_name,
                    'details': details,
                    'features': features,
                    'url': response.url,
                    'scraped_at': response.headers.get('Date', ''),
                }
                
                op_logger.info("Successfully extracted product", 
                              product_name=product_name,
                              details_count=len(details),
                              features_count=len(features))
                
                self.context.record_items_scraped("extract_product", "product", 1)
                
                yield product
                
            except Exception as e:
                op_logger.error("Failed to extract product data", error=str(e))
    
    def closed(self, reason):
        """Called when spider closes."""
        self.context.logger.info("Spider closed", reason=reason)
        self.context.shutdown()
```

2. **Run your monitored spider:**
```bash
cd /Users/benlokos/development/Scrapers/ruger_scraper
scrapy crawl ruger_spider_monitored
```

## What You Get

### 1. Structured JSON Logging
All logs are formatted as JSON for easy ingestion by Loki:
```json
{
  "timestamp": "2023-12-01T10:30:00.000Z",
  "level": "info",
  "scraper_name": "ruger_scraper",
  "operation": "extract_product",
  "url": "https://ruger.com/products/...",
  "status": "success",
  "items_scraped": 1,
  "duration_seconds": 2.5
}
```

### 2. Prometheus Metrics
Available at `http://localhost:8000/metrics`:
- `scraper_requests_total{operation="extract_product",status="success"}`
- `scraper_duration_seconds{operation="extract_product"}`
- `scraper_items_scraped_total{item_type="product"}`
- `scraper_http_requests_total{status_code="200"}`
- `scraper_errors_total{error_type="TimeoutError"}`
- System metrics (CPU, memory usage)

### 3. Health Checks
Available at `http://localhost:8001/health`:
- Overall scraper health status
- CPU and memory usage checks
- Custom checks (like start URL reachability)

### 4. Monitoring Integration
Works seamlessly with your existing Grafana/Loki/Prometheus stack:
- Logs automatically go to Loki
- Metrics are scraped by Prometheus
- View everything in Grafana dashboards

## Environment Variables

You can configure monitoring without changing code:

```bash
export LOKI_URL="http://your-loki:3100"
export PROMETHEUS_URL="http://your-prometheus:9090"
export GRAFANA_URL="http://your-grafana:3000"
export SCRAPER_NAME="ruger_scraper"
export ENVIRONMENT="production"
export LOG_LEVEL="INFO"
export PROMETHEUS_PORT="8000"
export HEALTH_CHECK_PORT="8001"
```

## Docker Integration

Update your `docker-compose.yml` to expose monitoring ports:

```yaml
services:
  ruger-scraper:
    # ... your existing config
    ports:
      - "8000:8000"  # Prometheus metrics
      - "8001:8001"  # Health checks
    environment:
      - LOKI_URL=http://loki:3100
      - PROMETHEUS_URL=http://prometheus:9090
      - ENVIRONMENT=production
```

## Grafana Dashboard Queries

Create dashboards with these queries:

### Scraping Success Rate
```promql
rate(scraper_requests_total{status="success"}[5m]) / rate(scraper_requests_total[5m]) * 100
```

### Items Scraped Per Hour
```promql
rate(scraper_items_scraped_total[1h]) * 3600
```

### Average Response Time
```promql
rate(scraper_http_response_duration_seconds_sum[5m]) / rate(scraper_http_response_duration_seconds_count[5m])
```

### Error Rate
```promql
rate(scraper_errors_total[5m])
```

## Benefits

1. **Centralized Configuration**: Change monitoring endpoints in one place
2. **Consistent Logging**: All scrapers use the same structured format
3. **Automatic Metrics**: No manual instrumentation needed
4. **Health Monitoring**: Built-in health checks for operational awareness
5. **Easy Debugging**: Rich context in logs helps troubleshoot issues
6. **Performance Tracking**: Monitor scraper performance over time
7. **Alerting Ready**: Metrics and logs ready for alerting rules

## Migration Path

1. Start with Option 1 (minimal integration) for immediate benefits
2. Gradually move to Option 2 for enhanced control
3. Add custom health checks and metrics as needed
4. Create Grafana dashboards for monitoring
5. Set up alerting based on metrics and logs

This approach ensures that all your scrapers (current and future) use consistent monitoring without duplicating configuration across projects.
