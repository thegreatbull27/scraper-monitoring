"""
Example: Scrapy spider with monitoring integration.
"""
import scrapy
from scraper_monitoring.scrapy_integration import MonitoredSpider


class ExampleSpider(MonitoredSpider):
    """Example spider with monitoring."""
    
    name = 'example_spider'
    start_urls = [
        'https://httpbin.org/json',
        'https://httpbin.org/user-agent',
        'https://httpbin.org/headers'
    ]
    
    def parse(self, response):
        """Parse response and extract data."""
        # Use monitoring context for this parsing operation
        with self.context.scrape_operation("parse_json", response.url, item_type="json_item") as op:
            op_logger = op['logger']
            
            try:
                data = response.json()
                
                # Create item
                item = {
                    'url': response.url,
                    'data': data,
                    'timestamp': response.headers.get('Date', ''),
                    'status_code': response.status
                }
                
                op_logger.info("Successfully parsed response", 
                              data_keys=list(data.keys()),
                              item_keys=list(item.keys()))
                
                # Record that we scraped an item
                self.context.record_items_scraped("parse_json", "json_item", 1)
                
                yield item
                
            except Exception as e:
                op_logger.error("Failed to parse response", error=str(e))
                # Error is automatically recorded by context manager


# Scrapy settings for this example
custom_settings = {
    'EXTENSIONS': {
        'scraper_monitoring.scrapy_integration.ScrapyMonitoringExtension': 100,
    },
    'PROMETHEUS_PORT': 8000,
    'HEALTH_CHECK_PORT': 8001,
    'LOG_LEVEL': 'INFO',
    'DOWNLOAD_DELAY': 1,  # Be nice to httpbin
}


if __name__ == "__main__":
    # Run with: scrapy crawl example_spider
    print("Run this spider with: scrapy crawl example_spider")
    print("Check metrics at: http://localhost:8000")
    print("Check health at: http://localhost:8001/health")
