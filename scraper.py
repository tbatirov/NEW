import trafilatura
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time
import logging
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback data in case websites are unreachable
FALLBACK_STANDARDS = [
    {
        "url": "https://www.mf.uz/media/file/state/method/BHMS/eng/1.pdf",
        "content": """
        NAS 1 - Accounting Policies and Financial Reporting
        
        Financial statements should include:
        1. Balance sheet
        2. Income statement
        3. Cash flow statement
        4. Notes to financial statements
        
        Classification principles:
        - Assets divided into current and non-current
        - Liabilities divided into current and non-current
        - Income and expenses classified by function
        """,
        "source": "fallback"
    },
    {
        "url": "https://www.mf.uz/media/file/state/method/BHMS/eng/21.pdf",
        "content": """
        NAS 21 - Chart of Accounts
        
        Main account categories:
        1. Assets (1000-2999)
        2. Liabilities (3000-5999)
        3. Equity (6000-6999)
        4. Income (7000-8999)
        5. Expenses (9000-9999)
        
        Classification rules:
        - Current assets: expected to be realized within 12 months
        - Non-current assets: expected to be held for more than 12 months
        - Current liabilities: due within 12 months
        - Non-current liabilities: due after 12 months
        """,
        "source": "fallback"
    }
]

def get_nsbu_links() -> List[str]:
    """Get all relevant links from nsbu.uz"""
    base_urls = [
        "https://nsbu.uz",
        "http://nsbu.uz",
        "https://www.nsbu.uz"
    ]
    standards_pages = [
        "/standards/accounting",
        "/standards",
        "/bhms",
        "/dokumenty"
    ]
    
    all_links = set()
    success = False
    
    for base_url in base_urls:
        if success:
            break
            
        for standards_page in standards_pages:
            try:
                url = base_url + standards_page
                logger.info(f"Trying to fetch from: {url}")
                
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                standard_links = [
                    link['href'] if link['href'].startswith('http') else base_url + link['href']
                    for link in links
                    if any(term in link['href'].lower() for term in ['bhms', 'standard', 'nsbu', 'положение'])
                ]
                
                all_links.update(standard_links)
                if standard_links:
                    success = True
                    logger.info(f"Successfully found {len(standard_links)} links from {url}")
                    break
                
            except Exception as e:
                logger.warning(f"Error fetching from {base_url + standards_page}: {str(e)}")
                continue
    
    return list(all_links)

def get_buxgalter_links() -> List[str]:
    """Get all relevant links from buxgalter.uz"""
    try:
        base_url = "https://buxgalter.uz"
        relevant_sections = [
            "",
            "/knowledges",
            "/documents",
            "/articles"
        ]
        
        all_links = set()
        
        for section in relevant_sections:
            try:
                url = base_url + section
                logger.info(f"Fetching from: {url}")
                
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
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
    except Exception as e:
        logger.error(f"Error accessing buxgalter.uz: {str(e)}")
        return []

def scrape_standards() -> List[Dict[str, str]]:
    """Scrape standards with fallback mechanism"""
    standards = []
    
    # Try to get links from both sources
    nsbu_links = get_nsbu_links()
    logger.info(f"Found {len(nsbu_links)} links from NSBU")
    
    buxgalter_links = get_buxgalter_links()
    logger.info(f"Found {len(buxgalter_links)} links from Buxgalter")
    
    all_links = list(set(nsbu_links + buxgalter_links))
    
    if all_links:
        logger.info(f"Total unique links to process: {len(all_links)}")
        
        for link in all_links:
            try:
                logger.info(f"Processing: {link}")
                
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
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error scraping {link}: {str(e)}")
                continue
    
    # If no standards were successfully scraped, use fallback data
    if not standards:
        logger.warning("No standards scraped from websites. Using fallback data.")
        standards = FALLBACK_STANDARDS
        
    logger.info(f"Successfully processed {len(standards)} standards")
    return standards
