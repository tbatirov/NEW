import trafilatura
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time

def get_nsbu_links() -> List[str]:
    """Get all relevant links from nsbu.uz"""
    base_url = "https://nsbu.uz"  # Updated URL without www
    standards_page = "/standards/accounting"  # Updated to actual standards page
    
    try:
        response = requests.get(base_url + standards_page)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # Filter for standard-related links
        standard_links = [
            link['href'] if link['href'].startswith('http') else base_url + link['href']
            for link in links
            if 'bhms' in link['href'].lower() or 'standard' in link['href'].lower()
        ]
        
        return list(set(standard_links))
    except Exception as e:
        print(f"Error fetching links: {e}")
        return []

def scrape_standards() -> List[Dict[str, str]]:
    """Scrape all accounting standards from nsbu.uz"""
    standards = []
    links = get_nsbu_links()
    
    for link in links:
        try:
            # Use trafilatura to extract clean text
            downloaded = trafilatura.fetch_url(link)
            text = trafilatura.extract(downloaded)
            
            if text:
                standards.append({
                    'url': link,
                    'content': text
                })
            
            # Respectful crawling
            time.sleep(1)
            
        except Exception as e:
            print(f"Error scraping {link}: {e}")
            continue
    
    return standards
