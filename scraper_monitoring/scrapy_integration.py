"""
Scrapy integration for the monitoring library.
"""
from typing import Optional, Dict, Any
import scrapy
from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.spiders import Spider
from scrapy.http import Request, Response

from .context import ScrapingContext
from .config import MonitoringConfig


class ScrapyMonitoringExtension:
    """Scrapy extension for monitoring integration."""
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.context = ScrapingContext(self.config)
        self.spider_start_times = {}
    
    @classmethod
    def from_crawler(cls, crawler: Crawler):
        """Create extension from crawler."""
        # Get config from Scrapy settings
        settings = crawler.settings
        
        config = MonitoringConfig(
            scraper_name=settings.get('BOT_NAME', 'scrapy_spider'),
            log_level=settings.get('LOG_LEVEL', 'INFO'),
            log_file=settings.get('LOG_FILE'),
            prometheus_port=settings.getint('PROMETHEUS_PORT', 8000),
            health_check_port=settings.getint('HEALTH_CHECK_PORT', 8001),
        )
        
        ext = cls(config)
        
        # Connect to Scrapy signals
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.request_scheduled, signal=signals.request_scheduled)
        crawler.signals.connect(ext.response_received, signal=signals.response_received)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        
        return ext
    
    def spider_opened(self, spider: Spider):
        """Handle spider opened signal."""
        self.spider_start_times[spider.name] = spider.crawler.stats.start_time
        self.context.logger.info("Spider started", spider=spider.name)
        
        # Add spider-specific health check
        def spider_health():
            return hasattr(spider, 'crawler') and spider.crawler is not None
        
        self.context.add_health_check(
            f"spider_{spider.name}",
            spider_health,
            f"Check if spider {spider.name} is running"
        )
    
    def spider_closed(self, spider: Spider, reason: str):
        """Handle spider closed signal."""
        self.context.logger.info("Spider closed", spider=spider.name, reason=reason)
        
        # Log final stats
        stats = spider.crawler.stats.get_stats()
        if stats:
            self.context.logger.info("Spider final stats", 
                                   spider=spider.name,
                                   stats=stats)
    
    def request_scheduled(self, request: Request, spider: Spider):
        """Handle request scheduled signal."""
        # Update queue size
        queue_size = len(spider.crawler.engine.slot.scheduler)
        self.context.update_queue_size("scheduled", queue_size)
    
    def response_received(self, response: Response, request: Request, spider: Spider):
        """Handle response received signal."""
        # Record HTTP metrics
        url_domain = response.url.split('/')[2] if '://' in response.url else 'unknown'
        self.context.metrics.record_http_request(
            request.method, str(response.status), url_domain
        )
        
        # Log response
        self.context.logger.debug("Response received",
                                 url=response.url,
                                 status=response.status,
                                 size=len(response.body))
    
    def item_scraped(self, item: Dict[str, Any], response: Response, spider: Spider):
        """Handle item scraped signal."""
        # Record item metrics
        item_type = item.__class__.__name__ if hasattr(item, '__class__') else 'item'
        self.context.record_items_scraped("scrape", item_type, 1)
    
    def spider_error(self, failure, response: Response, spider: Spider):
        """Handle spider error signal."""
        self.context.logger.error("Spider error",
                                 spider=spider.name,
                                 error=str(failure.value),
                                 url=response.url if response else 'unknown')


class MonitoredSpider(scrapy.Spider):
    """Base spider class with monitoring integration."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitoring_config = MonitoringConfig(scraper_name=self.name)
        self.context = ScrapingContext(self.monitoring_config)
    
    def start_requests(self):
        """Generate start requests with monitoring."""
        for url in self.start_urls:
            with self.context.scrape_operation("start_request", url):
                yield scrapy.Request(url, callback=self.parse)
    
    def parse(self, response):
        """Override this method in your spider."""
        raise NotImplementedError("Subclasses must implement parse method")
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.context.shutdown()
