# Finn.no Sailing Boat Scraper & Dashboard

An interactive data exploration tool for Finn.no sailing boat listings.

Dashboard available here: https://kpuafdnfdmf3k8rlqrtkwz.streamlit.app/

## Features

### Data Collection
- **Basic scraping**: Extract boat listings from Finn.no search results
- **Detailed scraping**: Fetch individual listing pages for full specifications
- **Comprehensive database**: Store 34 fields including price, length, year, location, specifications, equipment, and more

### Interactive Dashboard
- **Filter by**: Price, length, age, brand, type, material, fuel, location, equipment keywords
- **Visualizations**: Scatter plots, box plots, histograms, correlations, pie charts
- **Price Analysis**: Explore price relationships with length, age, and brand
- **Listing Browser**: Browse filtered results with images and full details

## Quick Start

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended)
uv pip install -r requirements.txt
```

### 2. Scrape Data

```bash
# Basic scrape (search results only)
python main.py --max-pages 2

# Detailed scrape (includes individual listing pages)
python main.py --max-pages 2 --scrape-details

# With custom settings
python main.py \
    --max-pages 3 \
    --scrape-details \
    --delay-min 1.0 \
    --delay-max 2.0 \
    --detail-delay-min 0.5 \
    --detail-delay-max 1.0
```

### 3. Run the Dashboard

```bash
streamlit run dashboard.py
```

Then open `http://localhost:8501` in your browser.

## CLI Options

### main.py (Scraper)

| Option | Description | Default |
|--------|-------------|---------|
| `--base-url` | Finn.no search URL | Standard sailing boat filter |
| `--db-path` | Database file path | `finn_boats.db` |
| `--max-pages` | Maximum pages to scrape | All pages |
| `--delay-min` | Min delay between requests (s) | 2.5 |
| `--delay-max` | Max delay between requests (s) | 5.0 |
| `--scrape-details` | Fetch individual listing pages | Disabled |
| `--detail-delay-min` | Min delay for detail pages (s) | 1.0 |
| `--detail-delay-max` | Max delay for detail pages (s) | 2.0 |
| `--verbose` | Enable verbose output | Disabled |

### analyze.py (Static Analysis)

```bash
python analyze.py --db-path finn_boats.db
```

### dashboard.py (Interactive Dashboard)

```bash
streamlit run dashboard.py
```

## Database Schema

The SQLite database (`finn_boats.db`) contains 34 fields including:

### Core Fields
- `id` - Finn.no listing ID
- `price` - Price in NOK (REAL)
- `brand` - Boat brand
- `model` - Boat model
- `title` - Listing title
- `url` - Finn.no URL
- `image` - Image URL

### Specifications
- `length` - Length in feet (REAL)
- `year_built` - Construction year (INTEGER)
- `type` - Boat type
- `material` - Construction material
- `fuel_type` - Fuel type
- `engine_manufacturer`, `engine_size`, `engine_type`
- `max_speed`, `weight`, `depth`, `width`
- `seating_capacity`, `sleeping_capacity`, `color`

### Location & Dates
- `location` - Postal code and city
- `boat_location` - General location
- `date_created`, `date_updated`, `scraped_at`

### Text Fields
- `announcement_text` - Short announcement
- `description` - Full description
- `equipment` - Equipment list
- `specifications` - Full specifications as JSON
- `finn_code` - Finn.no code

## Dashboard Features

### Overview Tab
- Key metrics (average price, range, age, length)
- Top brands by listing count
- Price distribution histogram

### Price Analysis Tab
- Price vs Length scatter (color by brand, size by age)
- Price vs Age scatter
- Price distribution by brand (box plots)
- Length vs Price with trendline

### Deep Dive Tab
- Correlation matrix heatmap
- Boat materials pie chart
- Year built distribution
- Engine manufacturers
- Equipment term frequency

### Listings Tab
- Paginated list with expandable cards
- Sort by price, year, length, or age
- Optional images and descriptions
- Direct links to Finn.no

## Rate Limiting

The scraper includes rate limiting to avoid being blocked:
- **Search pages**: 2.5-5.0 seconds between requests
- **Detail pages**: 1.0-2.0 seconds between requests
- **Automatic retries**: For timeouts and 5xx errors
- **429 handling**: Respects Retry-After headers

For faster testing:
```bash
python main.py --max-pages 1 --delay-min 0.5 --delay-max 1.0 --detail-delay-min 0.3 --detail-delay-max 0.5
```

## Project Structure

```
finn-scraper/
├── main.py              # CLI entry point
├── scraper.py           # Scraping logic
├── analyze.py           # Static analysis
├── dashboard.py         # Interactive Streamlit dashboard
├── pyproject.toml       # Project configuration
├── requirements.txt     # Dependencies
├── .gitignore           # Git ignore patterns
└── README.md            # Documentation
```

## Dependencies

- Python 3.10+
- beautifulsoup4
- matplotlib
- pandas
- plotly
- requests
- seaborn
- streamlit

## License

MIT License
