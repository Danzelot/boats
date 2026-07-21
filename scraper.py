import time
import random
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://www.finn.no/mobility/search/boat?class=2188&length_feet_from=33&length_feet_to=42&price_to=980000&sales_form=120&sales_form=121"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,no;q=0.8",
    "Referer": "https://www.finn.no/"
}



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

def scrape_single_page(url):
    """Fetches a specific page and extracts unique boat dictionary objects."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"   [Error] Page returned status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"   [Error] Connection timed out: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
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
        except (json.JSONDecodeError, TypeError):
            continue

    # Normalize structure and map fields cleanly
    boat_data = []
    for product in page_products:
        if not isinstance(product, dict):
            continue

        offers = product.get("offers", {})
        if not isinstance(offers, dict):
            offers = {}

        url_str = product.get("url", "")
        finn_id = url_str.split("/")[-1] if url_str else None

        if finn_id:
            boat_data.append({
                "ID": finn_id,
                "Title": product.get("name"),
                "Description": product.get("description"),
                "Brand/Type": product.get("brand", {}).get("name") if isinstance(product.get("brand"), dict) else product.get("brand"),
                "Price (NOK)": offers.get("price"),
                "URL": url_str,
                "Image": product.get("image")
            })

    # Deduplicate items localized to this specific page
    unique_page_boats = {b['ID']: b for b in boat_data}.values()
    return list(unique_page_boats)

def scrape_all_pages(base_url):
    """Loops through pagination variables until no more listings are found."""
    all_boats = {}
    page = 1

    while True:
        # Build the proper pagination URL query signature
        separator = "&" if "?" in base_url else "?"
        page_url = f"{base_url}{separator}page={page}"

        print(f"Scraping Page {page}...")
        boats_found = scrape_single_page(page_url)

        if not boats_found:
            print("No more boat listings found. Finished collection.")
            break

        # Count items before adding new data to gauge pagination status
        initial_count = len(all_boats)
        for boat in boats_found:
            all_boats[boat['ID']] = boat

        new_items_added = len(all_boats) - initial_count
        print(f"   -> Extracted {len(boats_found)} items ({new_items_added} new unique entries added)")

        # If a whole page provides zero brand new items, we have hit cyclical listings/end of index
        if new_items_added == 0 and page > 1:
            print("   -> Running into duplicate listings. Breaking loop.")
            break

        page += 1

        # Human behavior delay simulation (keeps you from getting IP banned)
        sleep_duration = random.uniform(2.5, 5.0)
        time.sleep(sleep_duration)

    return list(all_boats.values())

# Execute the pagination routine
final_dataset = scrape_all_pages(BASE_URL)

if final_dataset:
    df = pd.DataFrame(final_dataset)
    print("\n" + "="*40)
    print(f"SUCCESS: Total dataset contains {len(df)} unique sailing boats.")
    print("="*40)
    df.to_csv("finn_sailing_boats_all.csv", index=False)
