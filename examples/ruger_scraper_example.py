"""
Example: Integrating monitoring with existing Ruger scraper.
"""
import scrapy
from scraper_monitoring import ScrapingContext, MonitoringConfig
from scraper_monitoring.scrapy_integration import ScrapyMonitoringExtension


class MonitoredRugerSpider(scrapy.Spider):
    """Enhanced Ruger spider with monitoring."""
    
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
        
        # Add custom health checks
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
        """Parse main page and discover product categories."""
        with self.context.scrape_operation("discover_categories", response.url) as op:
            op_logger = op['logger']
            
            base_url = response.url
            nav_data_blocks = response.css('div.nav-data[data-cat="all"] ul li.clearfix a::attr(href)').getall()
            
            op_logger.info("Found category links", count=len(nav_data_blocks))
            
            for link in nav_data_blocks:
                if link.startswith('javascript') or not link.strip():
                    continue
                
                full_link = response.urljoin(link)
                yield response.follow(full_link, self.parse_intermediate_page)
            
            # Record categories discovered
            self.context.record_items_scraped("discover_categories", "category", len(nav_data_blocks))

    def parse_intermediate_page(self, response):
        """Parse intermediate category page."""
        with self.context.scrape_operation("discover_products", response.url) as op:
            op_logger = op['logger']
            
            base_url = response.url
            product_links = response.css(
                'div.product-thumb.handgun.de-overlay a.image-link::attr(href), '
                'div.product-thumb.long-gun.de-overlay a.image-link::attr(href)'
            ).getall()
            
            op_logger.info("Found product links", count=len(product_links))
            
            for link in product_links:
                full_link = response.urljoin(link)
                yield response.follow(full_link, self.parse_product)
            
            # Record products discovered
            self.context.record_items_scraped("discover_products", "product_link", len(product_links))

    def parse_product(self, response):
        """Parse individual product page."""
        with self.context.scrape_operation("extract_product", response.url, item_type="product") as op:
            op_logger = op['logger']
            
            try:
                # Extract product data
                product_name = ''.join(response.css('div.content.title h1 *::text').getall()).strip()
                specs_section = response.css('div.content.specs')
                details = {}

                for spec_group in specs_section.css('ul.big-specs, ul.small-specs'):
                    for spec in spec_group.css('li'):
                        key = spec.css('em::text, ::text').extract_first().strip(': ')
                        value = spec.css('span::text').extract_first(default='').strip()
                        if key and value:
                            details[key] = value

                features = [
                    feature.strip() 
                    for feature in specs_section.css('ul.features li p::text').getall()
                ]

                # Create product item
                product = {
                    'product_name': product_name,
                    'url': response.url,
                    'details': details,
                    'features': features,
                    'scraped_at': response.headers.get('Date', ''),
                    'scraper_version': '2.0.0'
                }
                
                op_logger.info("Successfully extracted product", 
                              product_name=product_name,
                              details_count=len(details),
                              features_count=len(features))
                
                # Record successful extraction
                self.context.record_items_scraped("extract_product", "product", 1)
                
                yield product
                
            except Exception as e:
                op_logger.error("Failed to extract product data", error=str(e))
                # Error metrics are automatically recorded by context manager
    
    def closed(self, reason):
        """Called when spider closes."""
        self.context.logger.info("Spider closed", reason=reason)
        
        # Get final health status
        health = self.context.get_health_status()
        self.context.logger.info("Final health status", health_status=health['status'])
        
        # Shutdown monitoring
        self.context.shutdown()


# Enhanced Scrapy settings with monitoring
SCRAPY_SETTINGS = {
    'BOT_NAME': 'ruger_scraper_monitored',
    
    # Monitoring extension
    'EXTENSIONS': {
        'scraper_monitoring.scrapy_integration.ScrapyMonitoringExtension': 100,
    },
    
    # Monitoring ports
    'PROMETHEUS_PORT': 8000,
    'HEALTH_CHECK_PORT': 8001,
    
    # Logging
    'LOG_ENABLED': True,
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': '/app/logs/scrapy.log',
    
    # Rate limiting (be respectful)
    'AUTOTHROTTLE_ENABLED': True,
    'AUTOTHROTTLE_START_DELAY': 5,
    'AUTOTHROTTLE_MAX_DELAY': 60,
    'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    'DOWNLOAD_DELAY': 2,
    'RANDOMIZE_DOWNLOAD_DELAY': True,
    'CONCURRENT_REQUESTS': 2,
    
    # Output
    'FEED_FORMAT': 'json',
    'FEED_URI': '/app/output/products_monitored.json',
    
    # User agent rotation
    'DOWNLOADER_MIDDLEWARES': {
        'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    },
}


if __name__ == "__main__":
    print("Enhanced Ruger Spider with Monitoring")
    print("=====================================")
    print("Features:")
    print("- Structured JSON logging for Grafana/Loki")
    print("- Prometheus metrics collection")
    print("- Health check endpoints")
    print("- Operation tracking and error handling")
    print()
    print("To run:")
    print("scrapy crawl ruger_spider_monitored")
    print()
    print("Monitoring endpoints:")
    print("- Metrics: http://localhost:8000")
    print("- Health: http://localhost:8001/health")
    print("- Readiness: http://localhost:8001/ready")
    print("- Liveness: http://localhost:8001/live")
