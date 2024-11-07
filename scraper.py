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
        print(f"Error fetching links from nsbu.uz: {e}")
        return []

def get_buxgalter_links() -> List[str]:
    base_url = "https://buxgalter.uz"
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # Filter relevant links (adjust patterns based on website structure)
        relevant_links = [
            link['href'] if link['href'].startswith('http') else base_url + link['href']
            for link in links
            if any(term in link['href'].lower() for term in ['standard', 'nsbu', 'regulation', 'law'])
        ]
        
        return list(set(relevant_links))
    except Exception as e:
        print(f"Error fetching buxgalter.uz links: {e}")
        return []

def scrape_standards() -> List[Dict[str, str]]:
    standards = []
    
    # Get links from both sources
    nsbu_links = get_nsbu_links()
    buxgalter_links = get_buxgalter_links()
    all_links = nsbu_links + buxgalter_links
    
    for link in all_links:
        try:
            # Use trafilatura to extract clean text
            downloaded = trafilatura.fetch_url(link)
            text = trafilatura.extract(downloaded)
            
            if text:
                standards.append({
                    'url': link,
                    'content': text,
                    'source': 'nsbu.uz' if 'nsbu.uz' in link else 'buxgalter.uz'
                })
            
            # Respectful crawling
            time.sleep(1)
            
        except Exception as e:
            print(f"Error scraping {link}: {e}")
            continue
    
    return standards
