import time
import random
import json
import sqlite3
import re
import datetime
from pathlib import Path
from typing import Optional, List, Dict
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.finn.no/mobility/search/boat?class=2188&length_feet_from=33&length_feet_to=42&price_to=980000&sales_form=120&sales_form=121"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,no;q=0.8",
    "Referer": "https://www.finn.no/"
}

MAX_RETRIES = 3
RETRY_DELAY = 5.0
REQUEST_DELAY = (2.5, 5.0)  # Random delay between requests


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


def get_db_connection(db_path="finn_boats.db"):
    """Create and return SQLite database connection with boats table."""
    Path(db_path).touch()  # Create file if not exists
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn):
    """Create boats table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boats (
            id TEXT PRIMARY KEY,
            price REAL,
            length REAL,
            location TEXT,
            brand TEXT,
            type TEXT,
            announcement_text TEXT,
            title TEXT,
            url TEXT,
            image TEXT,
            year_built INTEGER,
            date_created TEXT,
            date_updated TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def find_listings_recursively(data):
    """Recursively crawls a JSON object to find all valid product dictionaries."""
    results = []
    if isinstance(data, dict):
        if data.get("@type") == "ListItem" and isinstance(data.get("item"), dict):
            results.append(data["item"])
        elif data.get("@type") == "Product":
            results.append(data)
        else:
            for value in data.values():
                results.extend(find_listings_recursively(value))
    elif isinstance(data, list):
        for item in data:
            results.extend(find_listings_recursively(item))
    return results


def try_parse_float(value):
    """Safely parse a value to float, return None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError, AttributeError):
        return None


def try_parse_year(value):
    """Extract year from a date string."""
    if value is None:
        return None
    try:
        # Try to parse ISO date format
        if isinstance(value, str):
            # Try YYYY-MM-DD or similar
            dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.year
        return None
    except (ValueError, TypeError):
        # Try to extract 4-digit year from string
        if isinstance(value, str):
            match = re.search(r'\b(19|20)\d{2}\b', value)
            if match:
                return int(match.group())
        return None


def parse_boat_details(product):
    """Extract all required fields from a Product LD+JSON object."""
    offers = product.get("offers", {})
    if not isinstance(offers, dict):
        offers = {}
    
    url_str = product.get("url", "")
    finn_id = url_str.split("/")[-1] if url_str else None
    
    # Extract brand and type separately
    brand_obj = product.get("brand", {})
    if isinstance(brand_obj, dict):
        brand = brand_obj.get("name", "")
    else:
        brand = brand_obj or ""
    
    # Type might be in category or name
    boat_type = product.get("category", "") or ""
    
    # Clean brand - remove type suffix if present
    if brand:
        # Remove " Seilb\u00e5t/Motorseiler" or similar type suffixes
        brand = re.sub(r'\s*/\s*.*$', '', brand).strip()
        brand = re.sub(r'\s+Seilb\u00e5t/Motorseiler$', '', brand).strip()
        brand = re.sub(r'\s+Seilb\u00e5t$', '', brand).strip()
    
    # Try to extract location from contentLocation or address
    location = ""
    content_location = product.get("contentLocation", {})
    if isinstance(content_location, dict):
        location = content_location.get("name", "") or content_location.get("address", "")
    if not location:
        address = product.get("address", {})
        if isinstance(address, dict):
            location = address.get("addressLocality", "") or address.get("addressRegion", "")
    
    # Extract length - check various possible fields
    length = None
    additional_properties = product.get("additionalProperty", [])
    if isinstance(additional_properties, list):
        for prop in additional_properties:
            if isinstance(prop, dict):
                prop_name = prop.get("name", "").lower()
                if "length" in prop_name or "lengde" in prop_name:
                    length = try_parse_float(prop.get("value"))
                    break
    
    # Also check for length in the main product properties
    if length is None:
        if "length" in product:
            length = try_parse_float(product.get("length"))
    
    # Extract dates
    date_created = product.get("datePublished")  # Listing creation date
    date_updated = product.get("dateModified")   # Last update date
    
    # Extract year built - check releaseDate or additionalProperty
    year_built = None
    release_date = product.get("releaseDate")
    if release_date:
        year_built = try_parse_year(release_date)
    if not year_built:
        for prop in additional_properties:
            if isinstance(prop, dict):
                prop_name = prop.get("name", "").lower()
                if "year" in prop_name or "\u00e5r" in prop_name or "bygg" in prop_name:
                    year_built = try_parse_year(prop.get("value"))
                    break
    
    return {
        "id": finn_id,
        "price": try_parse_float(offers.get("price")),
        "length": length,
        "location": location.strip() if location else None,
        "brand": brand.strip() if brand else None,
        "type": boat_type.strip() if boat_type else None,
        "announcement_text": product.get("description"),
        "title": product.get("name"),
        "url": url_str,
        "image": product.get("image"),
        "year_built": year_built,
        "date_created": date_created,
        "date_updated": date_updated
    }


def make_request(url: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """Make HTTP request with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("Retry-After", RETRY_DELAY)
                print(f"   [Warning] Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(float(retry_after) + random.uniform(1, 3))
                continue
            elif response.status_code >= 500:
                print(f"   [Warning] Server error {response.status_code}. Retrying...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print(f"   [Error] HTTP {response.status_code} for {url}")
                return None
        except requests.exceptions.Timeout:
            print(f"   [Warning] Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            continue
        except requests.exceptions.RequestException as e:
            print(f"   [Error] Request failed: {e}")
            return None
    return None


def save_to_database(boats_data: List[Dict], db_path: str = "finn_boats.db", verbose: bool = False) -> int:
    """Save boat data to SQLite database."""
    conn = get_db_connection(db_path)
    initialize_database(conn)
    
    inserted_count = 0
    updated_count = 0
    
    for boat in boats_data:
        try:
            # Check if already exists
            existing = conn.execute(
                "SELECT id FROM boats WHERE id = ?", (boat['id'],)
            ).fetchone()
            
            if existing:
                # Update existing record
                conn.execute("""
                    UPDATE boats SET 
                        price = ?, length = ?, location = ?,
                        brand = ?, type = ?, announcement_text = ?,
                        title = ?, url = ?, image = ?,
                        year_built = ?, date_created = ?, date_updated = ?,
                        scraped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    boat['price'], boat['length'], boat['location'],
                    boat['brand'], boat['type'], boat['announcement_text'],
                    boat['title'], boat['url'], boat['image'],
                    boat.get('year_built'), boat.get('date_created'), boat.get('date_updated'),
                    boat['id']
                ))
                updated_count += 1
                if verbose:
                    print(f"   [Debug] Updated boat {boat.get('id')}")
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO boats (
                        id, price, length, location, brand, type, 
                        announcement_text, title, url, image,
                        year_built, date_created, date_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    boat['id'], boat['price'], boat['length'], boat['location'],
                    boat['brand'], boat['type'], boat['announcement_text'],
                    boat['title'], boat['url'], boat['image'],
                    boat.get('year_built'), boat.get('date_created'), boat.get('date_updated')
                ))
                inserted_count += 1
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"   [DB Error] Failed to save boat {boat.get('id')}: {e}")
            conn.rollback()
    
    print(f"   -> Saved {inserted_count} new boats, updated {updated_count} existing boats to database")
    
    conn.close()
    return inserted_count


def scrape_single_page(url: str, verbose: bool = False) -> List[Dict]:
    """Fetches a specific page and extracts boat data."""
    html = make_request(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    ld_json_tags = soup.find_all('script', type='application/ld+json')
    
    page_products = []
    for tag in ld_json_tags:
        try:
            if not tag.string:
                continue
            data = json.loads(tag.string)
            found = find_listings_recursively(data)
            if found:
                page_products.extend(found)
        except (json.JSONDecodeError, TypeError) as e:
            if verbose:
                print(f"   [Debug] JSON parsing error: {e}")
            continue
    
    # Parse boat details with new function
    boat_data = []
    for product in page_products:
        if not isinstance(product, dict):
            continue
        parsed = parse_boat_details(product)
        if parsed and parsed.get('id'):  # Only add if we have an ID
            boat_data.append(parsed)
    
    return boat_data


def scrape_all_pages(
    base_url: str, 
    db_path: str = "finn_boats.db",
    max_pages: Optional[int] = None,
    delay_range: tuple = REQUEST_DELAY,
    verbose: bool = False
) -> int:
    """Scrape all pages and save to database. Returns total count of new insertions."""
    all_boats = {}
    page = 1
    total_saved = 0
    
    while True:
        # Check if we've hit max_pages limit
        if max_pages is not None and page > max_pages:
            print(f"   -> Reached maximum page limit of {max_pages}. Stopping.")
            break
            
        separator = "&" if "?" in base_url else "?"
        page_url = f"{base_url}{separator}page={page}"
        
        print(f"Scraping Page {page}...")
        boats_found = scrape_single_page(page_url, verbose=verbose)
        
        if not boats_found:
            print("No more boat listings found. Finished collection.")
            break
        
        # Deduplicate
        initial_count = len(all_boats)
        for boat in boats_found:
            all_boats[boat['id']] = boat
        
        new_items_added = len(all_boats) - initial_count
        print(f"   -> Extracted {len(boats_found)} items ({new_items_added} new unique entries)")
        
        if new_items_added == 0 and page > 1:
            print("   -> Running into duplicate listings. Breaking loop.")
            break
        
        page += 1
        
        # Rate limiting
        sleep_duration = random.uniform(*delay_range)
        print(f"   -> Waiting {sleep_duration:.1f}s before next request...")
        time.sleep(sleep_duration)
    
    # Save to database
    if all_boats:
        total_saved = save_to_database(list(all_boats.values()), db_path, verbose=verbose)
    
    return total_saved
