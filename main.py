import argparse
from scraper import scrape_all_pages, BASE_URL


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Finn.no sailing boat listings and save to SQLite database"
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Base URL for Finn.no boat search (default: %(default)s)"
    )
    parser.add_argument(
        "--db-path",
        default="finn_boats.db",
        help="Path to SQLite database file (default: %(default)s)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scrape (default: all)"
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=2.5,
        help="Minimum delay between requests in seconds (default: %(default)s)"
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=5.0,
        help="Maximum delay between requests in seconds (default: %(default)s)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("Starting Finn.no sailing boat scraper...")
    print(f"Target URL: {args.base_url}")
    print(f"Database: {args.db_path}")
    if args.max_pages:
        print(f"Max pages: {args.max_pages}")
    print(f"Delay range: {args.delay_min}s - {args.delay_max}s")
    if args.verbose:
        print("Verbose mode: enabled")
    print()
    
    total_saved = scrape_all_pages(
        args.base_url,
        db_path=args.db_path,
        max_pages=args.max_pages,
        delay_range=(args.delay_min, args.delay_max),
        verbose=args.verbose
    )
    
    print("\n" + "="*40)
    if total_saved > 0:
        print(f"SUCCESS: Saved {total_saved} new boat listings to {args.db_path}")
    else:
        print("WARNING: No new boat listings were saved")
    print("="*40)


if __name__ == "__main__":
    main()
