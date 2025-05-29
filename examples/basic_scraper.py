"""
Example: Basic scraper with monitoring integration.
"""
import time
import requests
from scraper_monitoring import ScrapingContext, MonitoringConfig


def scrape_website_basic():
    """Basic scraper example."""
    # Configure monitoring
    config = MonitoringConfig(
        scraper_name="example_scraper",
        scraper_version="1.0.0",
        environment="development",
        log_level="INFO"
    )
    
    # Use context manager for automatic monitoring
    with ScrapingContext(config) as ctx:
        logger = ctx.get_logger("main")
        logger.info("Starting basic scraper example")
        
        urls = [
            "https://httpbin.org/json",
            "https://httpbin.org/user-agent",
            "https://httpbin.org/headers"
        ]
        
        all_items = []
        
        for url in urls:
            # Track each page scraping operation
            with ctx.scrape_operation("page_scrape", url, item_type="json_data") as op:
                op_logger = op['logger']
                
                try:
                    # Make HTTP request with tracking
                    with ctx.page_request(url) as req:
                        req_logger = req['logger']
                        req_logger.info("Making HTTP request")
                        
                        response = requests.get(url)
                        response.raise_for_status()
                        
                        # Log response details
                        ctx.metrics.record_http_request("GET", str(response.status_code), 
                                                       url.split('/')[2])
                    
                    # Process response
                    data = response.json()
                    all_items.append(data)
                    
                    # Record successful scraping
                    ctx.record_items_scraped("page_scrape", "json_data", 1)
                    
                    op_logger.info("Successfully scraped page", 
                                  status_code=response.status_code,
                                  data_keys=list(data.keys()))
                    
                except Exception as e:
                    op_logger.error("Failed to scrape page", error=str(e))
                    # Error is automatically recorded by context manager
                    continue
                
                # Simulate some processing time
                time.sleep(1)
        
        logger.info("Scraping completed", total_items=len(all_items))
        return all_items


if __name__ == "__main__":
    items = scrape_website_basic()
    print(f"Scraped {len(items)} items")
    print("Check metrics at: http://localhost:8000")
    print("Check health at: http://localhost:8001/health")
