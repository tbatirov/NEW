import trafilatura
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_nsbu_links() -> List[str]:
    """Get all relevant links from nsbu.uz"""
    base_urls = [
        "https://nsbu.uz",  # Primary URL
        "http://nsbu.uz",   # Alternative without HTTPS
        "https://www.nsbu.uz"  # Alternative with www
    ]
    standards_pages = [
        "/standards/accounting",
        "/standards",
        "/bhms",
        "/dokumenty"  # Common Russian translation
    ]
    
    all_links = set()
    
    for base_url in base_urls:
        for standards_page in standards_pages:
            try:
                url = base_url + standards_page
                logger.info(f"Trying to fetch from: {url}")
                
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                # Filter for standard-related links
                standard_links = [
                    link['href'] if link['href'].startswith('http') else base_url + link['href']
                    for link in links
                    if any(term in link['href'].lower() for term in ['bhms', 'standard', 'nsbu', 'положение'])
                ]
                
                all_links.update(standard_links)
                logger.info(f"Successfully found {len(standard_links)} links from {url}")
                break  # If successful, no need to try other variations
                
            except Exception as e:
                logger.warning(f"Error fetching from {base_url + standards_page}: {str(e)}")
                continue
    
    return list(all_links)

def get_buxgalter_links() -> List[str]:
    base_url = "https://buxgalter.uz"
    relevant_sections = [
        "",  # Home page
        "/knowledges",
        "/documents",
        "/articles"
    ]
    
    all_links = set()
    
    for section in relevant_sections:
        try:
            url = base_url + section
            logger.info(f"Fetching from: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            
            # Filter relevant links
            relevant_links = [
                link['href'] if link['href'].startswith('http') else base_url + link['href']
                for link in links
                if any(term in link['href'].lower() for term in 
                      ['standard', 'nsbu', 'regulation', 'law', 'bhms', 'положение', 'стандарт'])
            ]
            
            all_links.update(relevant_links)
            logger.info(f"Found {len(relevant_links)} relevant links from {url}")
            
        except Exception as e:
            logger.warning(f"Error fetching from {url}: {str(e)}")
            continue
    
    return list(all_links)

def scrape_standards() -> List[Dict[str, str]]:
    standards = []
    
    # Get links from both sources
    nsbu_links = get_nsbu_links()
    logger.info(f"Found {len(nsbu_links)} links from NSBU")
    
    buxgalter_links = get_buxgalter_links()
    logger.info(f"Found {len(buxgalter_links)} links from Buxgalter")
    
    all_links = list(set(nsbu_links + buxgalter_links))
    logger.info(f"Total unique links to process: {len(all_links)}")
    
    for link in all_links:
        try:
            logger.info(f"Processing: {link}")
            
            # Use trafilatura to extract clean text
            downloaded = trafilatura.fetch_url(link)
            if downloaded is None:
                logger.warning(f"Could not download content from {link}")
                continue
                
            text = trafilatura.extract(downloaded)
            
            if text:
                standards.append({
                    'url': link,
                    'content': text,
                    'source': 'nsbu.uz' if 'nsbu.uz' in link else 'buxgalter.uz'
                })
                logger.info(f"Successfully extracted content from {link}")
            else:
                logger.warning(f"No content extracted from {link}")
            
            # Respectful crawling
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error scraping {link}: {str(e)}")
            continue
    
    logger.info(f"Successfully processed {len(standards)} standards")
    return standards
