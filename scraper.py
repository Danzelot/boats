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

BASE_URL = "https://www.finn.no/mobility/search/boat?class=2188&length_feet_from=35&length_feet_to=42&motor_ad_location=1&sales_form=120"
# BASE_URL = "https://www.finn.no/mobility/search/boat?class=2188&length_feet_from=33&length_feet_to=42&price_to=980000&sales_form=120&sales_form=121"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,no;q=0.8",
    "Referer": "https://www.finn.no/"
}

MAX_RETRIES = 3
RETRY_DELAY = 5.0
REQUEST_DELAY = (2.5, 5.0)  # Random delay between requests
DETAIL_DELAY = (1.0, 2.0)  # Random delay between individual listing requests


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
    """Create boats and price_history tables if not exists."""
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
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- New fields from individual listing pages
            description TEXT,
            equipment TEXT,
            specifications JSON,
            model TEXT,
            fuel_type TEXT,
            engine_included TEXT,
            engine_size TEXT,
            engine_manufacturer TEXT,
            engine_type TEXT,
            max_speed TEXT,
            material TEXT,
            weight TEXT,
            depth TEXT,
            width TEXT,
            seating_capacity TEXT,
            sleeping_capacity TEXT,
            color TEXT,
            registration_number TEXT,
            boat_location TEXT,
            finn_code TEXT
        )
    """)
    
    # Create price history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boat_id TEXT NOT NULL,
            price REAL NOT NULL,
            previous_price REAL,
            change_amount REAL,
            change_percent REAL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (boat_id) REFERENCES boats(id)
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
        if isinstance(value, str):
            dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.year
        return None
    except (ValueError, TypeError):
        if isinstance(value, str):
            match = re.search(r'\b(19|20)\d{2}\b', value)
            if match:
                return int(match.group())
        return None


def try_parse_int(value):
    """Safely parse a value to int, return None on failure."""
    if value is None:
        return None
    try:
        return int(str(value).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError, AttributeError):
        return None


def parse_boat_details(product):
    """Extract basic fields from a Product LD+JSON object."""
    offers = product.get("offers", {})
    if not isinstance(offers, dict):
        offers = {}
    
    url_str = product.get("url", "")
    finn_id = url_str.split("/")[-1] if url_str else None
    
    brand_obj = product.get("brand", {})
    if isinstance(brand_obj, dict):
        brand = brand_obj.get("name", "")
    else:
        brand = brand_obj or ""
    
    boat_type = product.get("category", "") or ""
    
    # Clean brand - remove type suffix if present
    if brand:
        brand = re.sub(r'\s*/\s*.*$', '', brand).strip()
        brand = re.sub(r'\s+Seilb\u00e5t/Motorseiler$', '', brand).strip()
        brand = re.sub(r'\s+Seilb\u00e5t$', '', brand).strip()
    
    return {
        "id": finn_id,
        "price": try_parse_float(offers.get("price")),
        "length": None,
        "location": None,
        "brand": brand.strip() if brand else None,
        "type": boat_type.strip() if boat_type else None,
        "announcement_text": product.get("description"),
        "title": product.get("name"),
        "url": url_str,
        "image": product.get("image"),
        "year_built": None,
        "date_created": None,
        "date_updated": None,
        # New fields - will be populated from detail page
        "description": None,
        "equipment": None,
        "specifications": None,
        "model": None,
        "fuel_type": None,
        "engine_included": None,
        "engine_size": None,
        "engine_manufacturer": None,
        "engine_type": None,
        "max_speed": None,
        "material": None,
        "weight": None,
        "depth": None,
        "width": None,
        "seating_capacity": None,
        "sleeping_capacity": None,
        "color": None,
        "registration_number": None,
        "boat_location": None,
        "finn_code": None
    }


def extract_text_after_heading(soup, heading_text):
    """Extract text content after a specific heading."""
    for h2 in soup.find_all('h2'):
        if heading_text in h2.get_text(strip=True):
            content = []
            next_node = h2.next_sibling
            while next_node and next_node.name != 'h2':
                if next_node.name in ['div', 'p', 'section', 'ul', 'ol', 'li', 'span']:
                    text = next_node.get_text(strip=True)
                    if text:
                        content.append(text)
                next_node = next_node.next_sibling
            return ' '.join(content)
    return None


def extract_specification_pairs(soup):
    """Extract key-value pairs from the specifications section."""
    specs = {}
    key_info = soup.find(class_='key-info-section')
    if key_info:
        items = key_info.find_all(['dt', 'dd'])
        for i in range(0, len(items), 2):
            if i + 1 < len(items):
                key = items[i].get_text(strip=True)
                value = items[i + 1].get_text(strip=True)
                specs[key] = value
    return specs


def extract_ad_info(soup):
    """Extract advertisement information (date, finn code, etc.)."""
    info = {}
    for h2 in soup.find_all('h2'):
        if 'Annonseinformasjon' in h2.get_text(strip=True):
            content = h2.get_text(strip=True)
            # Parse the text for FINN code and dates
            text = extract_text_after_heading(soup, 'Annonseinformasjon')
            if text:
                # Extract FINN-kode
                finn_code_match = re.search(r'FINN-kode\s*(\d+)', text)
                if finn_code_match:
                    info['finn_code'] = finn_code_match.group(1)
                
                # Extract Sist oppdatert (Last updated)
                date_match = re.search(r'Sist oppdatert\s*(\d+\.?\s*\w+\s*\d{4})', text)
                if date_match:
                    info['date_updated'] = date_match.group(1)
    return info


def scrape_listing_detail(url: str, verbose: bool = False) -> Optional[Dict]:
    """Scrape detailed information from an individual listing page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            if verbose:
                print(f"   [Debug] Detail page {url} returned status {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all sections
        description = extract_text_after_heading(soup, 'Beskrivelse')
        equipment = extract_text_after_heading(soup, 'Utstyr')
        specifications = extract_specification_pairs(soup)
        ad_info = extract_ad_info(soup)
        location = extract_text_after_heading(soup, 'Sted')
        
        # Parse specifications into individual fields
        # Extract numeric values from text (e.g., "38 fot" -> 38.0)
        def extract_numeric(value):
            """Extract numeric value from text like '38 fot' or '7 200 kg'."""
            if value is None:
                return None
            # Try to extract first number
            match = re.search(r'([\d]+(?:[.,]\d+)?)', str(value))
            if match:
                return try_parse_float(match.group(1))
            return None
        
        specs_dict = {
            "model": specifications.get('Modell'),
            "year_built": try_parse_year(specifications.get('Modellår')),
            "type": specifications.get('Type'),
            "fuel_type": specifications.get('Drivstoff'),
            "engine_included": specifications.get('Motor inkludert'),
            "engine_size": specifications.get('Motorstørrelse'),
            "engine_manufacturer": specifications.get('Motorfabrikant'),
            "engine_type": specifications.get('Type motor'),
            "max_speed": specifications.get('Topphastighet'),
            "material": specifications.get('Byggemateriale'),
            "weight": specifications.get('Vekt'),
            "length": extract_numeric(specifications.get('Lengde i fot')),
            "depth": extract_numeric(specifications.get('Dybde')),
            "width": extract_numeric(specifications.get('Bredde')),
            "seating_capacity": specifications.get('Sitteplasser'),
            "sleeping_capacity": specifications.get('Soveplasser'),
            "color": specifications.get('Farge'),
            "registration_number": specifications.get('Registreringsnummer'),
            "boat_location": specifications.get('Båtens beliggenhet'),
        }
        
        # Parse year_built
        year_text = specifications.get('Modellår')
        if year_text:
            specs_dict['year_built'] = try_parse_year(year_text)
        
        return {
            "description": description,
            "equipment": equipment,
            "specifications": json.dumps(specifications, ensure_ascii=False),
            "date_updated": ad_info.get('date_updated'),
            "finn_code": ad_info.get('finn_code'),
            "location": location,
            **specs_dict
        }
    
    except requests.exceptions.Timeout:
        if verbose:
            print(f"   [Warning] Detail page timeout for {url}")
        return None
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"   [Error] Detail page request failed for {url}: {e}")
        return None
    except Exception as e:
        if verbose:
            print(f"   [Error] Detail page parsing failed for {url}: {e}")
        return None


def make_request(url: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """Make HTTP request with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
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
    price_changes = 0
    new_listings = 0
    
    for boat in boats_data:
        try:
            # Check if already exists and get current price for history tracking
            existing = conn.execute(
                "SELECT id, price FROM boats WHERE id = ?", (boat['id'],)
            ).fetchone()
            
            if existing:
                # Get existing price for history tracking
                existing_price = existing['price']
                new_price = boat['price']
                
                # Update existing record
                conn.execute("""
                    UPDATE boats SET 
                        price = ?, length = ?, location = ?,
                        brand = ?, type = ?, announcement_text = ?,
                        title = ?, url = ?, image = ?,
                        year_built = ?, date_created = ?, date_updated = ?,
                        description = ?, equipment = ?, specifications = ?,
                        model = ?, fuel_type = ?, engine_included = ?,
                        engine_size = ?, engine_manufacturer = ?, engine_type = ?,
                        max_speed = ?, material = ?, weight = ?,
                        depth = ?, width = ?, seating_capacity = ?,
                        sleeping_capacity = ?, color = ?, registration_number = ?,
                        boat_location = ?, finn_code = ?,
                        scraped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    boat['price'], boat.get('length'), boat.get('location'),
                    boat['brand'], boat['type'], boat['announcement_text'],
                    boat['title'], boat['url'], boat['image'],
                    boat.get('year_built'), boat.get('date_created'), boat.get('date_updated'),
                    boat.get('description'), boat.get('equipment'), boat.get('specifications'),
                    boat.get('model'), boat.get('fuel_type'), boat.get('engine_included'),
                    boat.get('engine_size'), boat.get('engine_manufacturer'), boat.get('engine_type'),
                    boat.get('max_speed'), boat.get('material'), boat.get('weight'),
                    boat.get('depth'), boat.get('width'), boat.get('seating_capacity'),
                    boat.get('sleeping_capacity'), boat.get('color'), boat.get('registration_number'),
                    boat.get('boat_location'), boat.get('finn_code'),
                    boat['id']
                ))
                
                # Track price history if price changed
                if existing_price != new_price and existing_price is not None and new_price is not None:
                    change_amount = new_price - existing_price
                    change_percent = (change_amount / existing_price * 100) if existing_price != 0 else 0
                    
                    conn.execute("""
                        INSERT INTO price_history 
                        (boat_id, price, previous_price, change_amount, change_percent)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        boat['id'],
                        new_price,
                        existing_price,
                        change_amount,
                        change_percent
                    ))
                    if verbose:
                        change_sign = "+" if change_amount >= 0 else ""
                        print(f"   [Price Change] {boat['id']}: {existing_price:,.0f} -> {new_price:,.0f} NOK ({change_sign}{change_amount:,.0f}, {change_sign}{change_percent:.1f}%)")
                    price_changes += 1
                
                updated_count += 1
                if verbose:
                    print(f"   [Debug] Updated boat {boat.get('id')}")
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO boats (
                        id, price, length, location, brand, type, 
                        announcement_text, title, url, image,
                        year_built, date_created, date_updated,
                        description, equipment, specifications,
                        model, fuel_type, engine_included,
                        engine_size, engine_manufacturer, engine_type,
                        max_speed, material, weight,
                        depth, width, seating_capacity,
                        sleeping_capacity, color, registration_number,
                        boat_location, finn_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    boat['id'], boat['price'], boat.get('length'), boat.get('location'),
                    boat['brand'], boat['type'], boat['announcement_text'],
                    boat['title'], boat['url'], boat['image'],
                    boat.get('year_built'), boat.get('date_created'), boat.get('date_updated'),
                    boat.get('description'), boat.get('equipment'), boat.get('specifications'),
                    boat.get('model'), boat.get('fuel_type'), boat.get('engine_included'),
                    boat.get('engine_size'), boat.get('engine_manufacturer'), boat.get('engine_type'),
                    boat.get('max_speed'), boat.get('material'), boat.get('weight'),
                    boat.get('depth'), boat.get('width'), boat.get('seating_capacity'),
                    boat.get('sleeping_capacity'), boat.get('color'), boat.get('registration_number'),
                    boat.get('boat_location'), boat.get('finn_code')
                ))
                
                # Record initial price in history
                new_price = boat['price']
                if new_price is not None:
                    conn.execute("""
                        INSERT INTO price_history 
                        (boat_id, price, previous_price, change_amount, change_percent)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        boat['id'],
                        new_price,
                        None,  # No previous price for first entry
                        None,  # No change amount for first entry
                        None   # No change percent for first entry
                    ))
                    if verbose:
                        print(f"   [New Listing] {boat['id']}: Initial price {new_price:,.0f} NOK")
                    new_listings += 1
                
                inserted_count += 1
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"   [DB Error] Failed to save boat {boat.get('id')}: {e}")
            conn.rollback()
    
    # Print summary with price history info
    summary_parts = []
    if inserted_count > 0:
        summary_parts.append(f"{inserted_count} new boats")
    if updated_count > 0:
        summary_parts.append(f"{updated_count} updated")
    if price_changes > 0:
        summary_parts.append(f"{price_changes} price changes")
    if new_listings > 0:
        summary_parts.append(f"{new_listings} with initial prices")
    
    if summary_parts:
        print(f"   -> Saved {', '.join(summary_parts)} to database")
    
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
        if parsed and parsed.get('id'):
            boat_data.append(parsed)
    
    return boat_data


def scrape_all_pages(
    base_url: str, 
    db_path: str = "finn_boats.db",
    max_pages: Optional[int] = None,
    delay_range: tuple = REQUEST_DELAY,
    verbose: bool = False,
    scrape_details: bool = False,
    detail_delay_range: tuple = DETAIL_DELAY
) -> int:
    """Scrape all pages and save to database. Returns total count of new insertions.
    
    Args:
        scrape_details: If True, fetch individual listing pages for more data
        detail_delay_range: Delay between individual listing requests
    """
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
    
    # Optionally scrape detail pages for each boat
    if scrape_details and all_boats:
        total_boats = len(all_boats)
        print(f"\nScraping detailed information for {total_boats} listings...")
        print("[" + " " * 50 + "]", end="\r")  # Initial progress bar
        detail_count = 0
        
        for idx, (boat_id, boat) in enumerate(all_boats.items(), 1):
            if boat.get('url'):
                # Update progress bar
                progress = int((idx / total_boats) * 50)
                bar = "█" * progress + " " * (50 - progress)
                print(f"[{bar}] {idx}/{total_boats} ({idx/total_boats:.0%}) - {boat_id}", end="\r")
                
                details = scrape_listing_detail(boat['url'], verbose=verbose)
                if details:
                    # Merge details into boat record
                    all_boats[boat_id].update(details)
                    detail_count += 1
                    # Update length from specifications
                    if details.get('length'):
                        all_boats[boat_id]['length'] = details['length']
                    # Update location
                    if details.get('location'):
                        all_boats[boat_id]['location'] = details['location']
                    # Update year_built
                    if details.get('year_built'):
                        all_boats[boat_id]['year_built'] = details['year_built']
                    # Update date_updated
                    if details.get('date_updated'):
                        all_boats[boat_id]['date_updated'] = details['date_updated']
                
                # Rate limiting for detail pages
                sleep_duration = random.uniform(*detail_delay_range)
                time.sleep(sleep_duration)
        
        # Print final progress (new line)
        print(f"[{'█' * 50}] {total_boats}/{total_boats} (100%)")
        print(f"   -> Scraped details for {detail_count}/{total_boats} listings")
    
    # Save to database
    if all_boats:
        total_saved = save_to_database(list(all_boats.values()), db_path, verbose=verbose)
    
    return total_saved
