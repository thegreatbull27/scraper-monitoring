"""
Example: Using decorators for monitoring.
"""
import time
import requests
from scraper_monitoring import (
    track_scrape_operation, 
    track_page_scrape, 
    MonitoringConfig,
    ScraperLogger,
    ScraperMetrics
)


# Initialize monitoring components
config = MonitoringConfig(
    scraper_name="decorator_example",
    scraper_version="1.0.0"
)
logger = ScraperLogger(config)
metrics = ScraperMetrics(config)


@track_page_scrape(logger=logger, metrics=metrics)
def fetch_page(url: str):
    """Fetch a page with automatic monitoring."""
    response = requests.get(url)
    response.raise_for_status()
    return response


@track_scrape_operation(
    operation_name="json_extraction", 
    item_type="json_item",
    logger=logger, 
    metrics=metrics
)
def extract_data(response):
    """Extract data from response with monitoring."""
    data = response.json()
    
    # Return list to demonstrate item counting
    return [data]


def main():
    """Main scraping function using decorators."""
    logger.info("Starting decorator example")
    
    urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/headers"
    ]
    
    all_items = []
    
    for url in urls:
        try:
            # Fetch page (automatically tracked)
            response = fetch_page(url)
            
            # Extract data (automatically tracked)
            items = extract_data(response)
            all_items.extend(items)
            
            logger.info("Processed URL successfully", 
                       url=url, 
                       items_count=len(items))
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error("Failed to process URL", url=url, error=str(e))
            continue
    
    logger.info("Scraping completed", total_items=len(all_items))
    return all_items


if __name__ == "__main__":
    items = main()
    print(f"Scraped {len(items)} items using decorators")
    print("Check metrics at: http://localhost:8000")
    print("Check health at: http://localhost:8001/health")
