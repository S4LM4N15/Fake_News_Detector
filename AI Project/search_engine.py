import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """
    Search engine interface keeping the original name for compatibility, 
    but utilizing Google News RSS feed for 100% reliable free scraping.
    """
    return search_google_news(query, max_results)

def search_google_news(query: str, max_results: int = 10) -> list[dict]:
    """
    Scrapes Google News RSS for the given query. 
    It is extremely reliable and does not trigger anti-bot protections.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    results = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        # Parse XML
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
        
        for item in items[:max_results]:
            title_node = item.find("title")
            link_node = item.find("link")
            date_node = item.find("pubDate")
            source_node = item.find("source")
            
            if not title_node or not link_node:
                continue
                
            title = title_node.text.strip()
            link = link_node.text.strip()
            date = date_node.text.strip() if date_node else ""
            
            # Google news titles append " - Publisher Name" at the end. Strip it for cleaner matching.
            clean_title = re.sub(r' - [^-]+$', '', title)
            
            # Try to get the domain from the source node if available
            source_name = source_node.text.strip() if source_node else ""
            source_url = source_node.get("url", "") if source_node else ""
            
            from urllib.parse import urlparse
            true_domain = urlparse(source_url).netloc.lower().replace("www.", "") if source_url else ""
            
            # Decode the Google News redirect URL to the direct publisher URL
            direct_link = link
            try:
                from googlenewsdecoder import new_decoderv1
                decoded = new_decoderv1(link)
                if decoded and decoded.get("decoded_url"):
                    direct_link = decoded.get("decoded_url")
            except Exception:
                pass # fallback to Google News link if decoder fails
            
            results.append({
                "title": clean_title,
                "url": direct_link,  # Direct link for UI
                "display_url": source_name if source_name else link,
                "snippet": title,
                "date": date,
                "true_domain": true_domain
            })
            
    except Exception as e:
        print(f"[search_engine] Google News RSS error: {e}")
        
    return results
