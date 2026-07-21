"""
Norwegian postal code to fylke (county) mapping.
Based on official Norwegian postal code ranges.
"""


def get_fylke_from_postal_code(postal_code_str):
    """
    Map a Norwegian postal code to its fylke (county).
    
    Args:
        postal_code_str: String like "3145 Tjøme" or "3145" or just "3145"
    
    Returns:
        str: Fylke name or "Unknown" if not found
    """
    if not postal_code_str:
        return "Unknown"
    
    # Extract just the numeric part
    postal_code = str(postal_code_str).split()[0].strip()
    
    try:
        code = int(postal_code)
    except (ValueError, TypeError):
        return "Unknown"
    
    # Norwegian postal code ranges by fylke
    # Based on: https://no.wikipedia.org/wiki/Postnumre_i_Norge
    
    # Oslo
    if 1 <= code <= 999:
        return "Oslo"
    
    # Akershus (includes some Oslo area codes)
    if 1000 <= code <= 1485:
        return "Akershus"
    if 2000 <= code <= 2050:
        return "Akershus"
    
    # Østfold
    if 1500 <= code <= 1599:
        return "Østfold"
    if 1600 <= code <= 1699:
        return "Østfold"
    if 1700 <= code <= 1799:
        return "Østfold"
    if 1800 <= code <= 1924:
        return "Østfold"
    
    # Hedmark
    if 2200 <= code <= 2349:
        return "Hedmark"
    if 2350 <= code <= 2429:
        return "Hedmark"
    if 2430 <= code <= 2489:
        return "Hedmark"
    if 2500 <= code <= 2599:
        return "Hedmark"
    
    # Oppland
    if 2370 <= code <= 2399:
        return "Oppland"
    if 2440 <= code <= 2449:
        return "Oppland"
    if 2470 <= code <= 2479:
        return "Oppland"
    if 2600 <= code <= 2999:
        return "Oppland"
    
    # Buskerud
    if 3000 <= code <= 3499:
        return "Buskerud"
    if 3500 <= code <= 3599:
        return "Buskerud"
    
    # Vestfold
    if 3100 <= code <= 3199:
        return "Vestfold"
    if 3200 <= code <= 3299:
        return "Vestfold"
    
    # Telemark
    if 3600 <= code <= 3699:
        return "Telemark"
    if 3700 <= code <= 3799:
        return "Telemark"
    if 3800 <= code <= 3899:
        return "Telemark"
    if 3900 <= code <= 3999:
        return "Telemark"
    
    # Aust-Agder
    if 4800 <= code <= 4999:
        return "Aust-Agder"
    
    # Vest-Agder
    if 4500 <= code <= 4799:
        return "Vest-Agder"
    if 4900 <= code <= 4999:
        return "Vest-Agder"
    
    # Rogaland
    if 4000 <= code <= 4299:
        return "Rogaland"
    if 4300 <= code <= 4359:
        return "Rogaland"
    if 5500 <= code <= 5599:
        return "Rogaland"
    
    # Hordaland (now Vestland)
    if 5000 <= code <= 5499:
        return "Vestland"
    if 5500 <= code <= 5799:
        return "Vestland"
    if 5800 <= code <= 5899:
        return "Vestland"
    
    # Sogn og Fjordane (now Vestland)
    if 5700 <= code <= 5799:
        return "Vestland"
    if 6700 <= code <= 6799:
        return "Vestland"
    if 6800 <= code <= 6899:
        return "Vestland"
    if 6900 <= code <= 6999:
        return "Vestland"
    
    # Møre og Romsdal
    if 6000 <= code <= 6099:
        return "Møre og Romsdal"
    if 6100 <= code <= 6199:
        return "Møre og Romsdal"
    if 6200 <= code <= 6599:
        return "Møre og Romsdal"
    if 6600 <= code <= 6699:
        return "Møre og Romsdal"
    
    # Trøndelag (Nord-Trøndelag + Sør-Trøndelag)
    if 7000 <= code <= 7499:
        return "Trøndelag"
    if 7500 <= code <= 7999:
        return "Trøndelag"
    
    # Nordland
    if 8000 <= code <= 8999:
        return "Nordland"
    
    # Troms
    if 9000 <= code <= 9299:
        return "Troms"
    if 9300 <= code <= 9499:
        return "Troms"
    
    # Finnmark
    if 9500 <= code <= 9999:
        return "Finnmark"
    
    # Svalbard and Jan Mayen
    if code == 9170 or code == 9171:
        return "Svalbard"
    if 8500 <= code <= 8517:
        return "Jan Mayen"
    
    return "Unknown"


def get_region_from_location(location_str):
    """
    Extract region (fylke) from a location string.
    
    Args:
        location_str: String like "3145 Tjøme" or "Oslo"
    
    Returns:
        str: Fylke name or "Unknown"
    """
    if not location_str:
        return "Unknown"
    
    location_str = str(location_str).strip()
    
    # Try to extract postal code first
    postal_code = None
    parts = location_str.split()
    for part in parts:
        if part.isdigit() and len(part) == 4:
            postal_code = part
            break
    
    if postal_code:
        return get_fylke_from_postal_code(postal_code)
    
    # If no postal code, try to match fylke names
    fylker = [
        "Oslo", "Akershus", "Østfold", "Hedmark", "Oppland",
        "Buskerud", "Vestfold", "Telemark", "Aust-Agder", "Vest-Agder",
        "Rogaland", "Vestland", "Møre og Romsdal", "Trøndelag",
        "Nordland", "Troms", "Finnmark", "Svalbard", "Jan Mayen"
    ]
    
    for fylke in fylker:
        if fylke.lower() in location_str.lower():
            return fylke
    
    return "Unknown"
