import os
import sqlite3
import json
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def get_db_connection(db_path="finn_boats.db"):
    """Get connection to SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Run the scraper first with --scrape-details for full data!")
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def clean_and_analyze_boats(db_path="finn_boats.db"):
    conn = get_db_connection(db_path)
    if not conn:
        return
    
    # Read data from SQLite
    df = pd.read_sql_query("SELECT * FROM boats", conn)
    conn.close()
    
    if df.empty:
        print(f"Error: No data found in {db_path}")
        return
    
    print("=" * 70)
    print("FINN.NO SAILING BOATS - DETAILED ANALYSIS")
    print("=" * 70)
    print()
    
    # Basic stats
    print(f"Total listings: {len(df)}")
    print()
    
    # Price analysis
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    print("PRICE STATISTICS:")
    print(f"  Range: {df['price'].min():,.0f} - {df['price'].max():,.0f} NOK")
    print(f"  Average: {df['price'].mean():,.0f} NOK")
    print(f"  Median: {df['price'].median():,.0f} NOK")
    print()
    
    # Brand analysis
    df_clean = df.dropna(subset=['brand'])
    df_clean['Clean_Brand'] = (
        df_clean['brand']
        .astype(str)
        .str.replace(" Seilb\u00e5t/Motorseiler", "", case=False, regex=False)
        .str.replace(" Seilb\u00e5t", "", case=False, regex=False)
        .str.strip()
    )
    df_clean = df_clean[~df_clean['Clean_Brand'].isin(['andre', 'nan', 'None', ''])]
    
    print("TOP 10 BRANDS BY LISTING COUNT:")
    print("-" * 50)
    top_brands = df_clean['Clean_Brand'].value_counts().head(10)
    for brand, count in top_brands.items():
        avg_price = df_clean[df_clean['Clean_Brand'] == brand]['price'].mean()
        print(f"  {brand:25s} - {count:3d} listings, avg: {avg_price:,.0f} NOK")
    print()
    
    # Year built analysis
    year_data = df.dropna(subset=['year_built'])
    if len(year_data) > 0:
        print("YEAR BUILT DISTRIBUTION:")
        print("-" * 50)
        year_counts = year_data['year_built'].astype(int).value_counts().sort_index()
        # Group by decade
        year_data['decade'] = (year_data['year_built'] // 10) * 10
        decade_counts = year_data['decade'].value_counts().sort_index()
        for decade, count in decade_counts.items():
            avg_price = year_data[year_data['decade'] == decade]['price'].mean()
            print(f"  {decade}s: {count:3d} boats, avg price: {avg_price:,.0f} NOK")
        print()
    
    # Length analysis
    length_data = df.dropna(subset=['length'])
    if len(length_data) > 0:
        print("LENGTH DISTRIBUTION:")
        print("-" * 50)
        print(f"  Range: {length_data['length'].min():.0f} - {length_data['length'].max():.0f} feet")
        print(f"  Average: {length_data['length'].mean():.1f} feet")
        print(f"  Median: {length_data['length'].median():.1f} feet")
        print()
    
    # Location analysis
    location_data = df.dropna(subset=['location'])
    if len(location_data) > 0:
        print("TOP LOCATIONS:")
        print("-" * 50)
        location_counts = location_data['location'].value_counts().head(10)
        for loc, count in location_counts.items():
            print(f"  {loc:30s} - {count:3d} listings")
        print()
    
    # Engine analysis
    engine_data = df.dropna(subset=['engine_manufacturer'])
    if len(engine_data) > 0:
        print("ENGINE MANUFACTURERS:")
        print("-" * 50)
        engine_counts = engine_data['engine_manufacturer'].value_counts().head(10)
        for manuf, count in engine_counts.items():
            print(f"  {manuf:25s} - {count:3d} boats")
        print()
    
    # Material analysis
    material_data = df.dropna(subset=['material'])
    if len(material_data) > 0:
        print("BOAT MATERIALS:")
        print("-" * 50)
        material_counts = material_data['material'].value_counts()
        for mat, count in material_counts.items():
            print(f"  {mat:25s} - {count:3d} boats")
        print()
    
    # Fuel type analysis
    fuel_data = df.dropna(subset=['fuel_type'])
    if len(fuel_data) > 0:
        print("FUEL TYPES:")
        print("-" * 50)
        fuel_counts = fuel_data['fuel_type'].value_counts()
        for fuel, count in fuel_counts.items():
            print(f"  {fuel:25s} - {count:3d} boats")
        print()
    
    # Price history analysis
    print("=" * 70)
    print("PRICE HISTORY ANALYSIS")
    print("=" * 70)
    print()
    
    conn = get_db_connection(db_path)
    if conn:
        ph_df = pd.read_sql_query("SELECT * FROM price_history ORDER BY scraped_at", conn)
        conn.close()
        
        if not ph_df.empty:
            print(f"Total price history entries: {len(ph_df)}")
            
            # Count boats with price history
            unique_boats = ph_df['boat_id'].nunique()
            print(f"Boats with price history: {unique_boats}")
            print()
            
            # Price changes (entries with previous_price)
            changes_df = ph_df.dropna(subset=['previous_price'])
            if len(changes_df) > 0:
                print("PRICE CHANGES:")
                print("-" * 50)
                
                # Summary stats
                avg_change = changes_df['change_amount'].mean()
                avg_change_pct = changes_df['change_percent'].mean()
                price_increases = len(changes_df[changes_df['change_amount'] > 0])
                price_decreases = len(changes_df[changes_df['change_amount'] < 0])
                
                print(f"  Total price changes: {len(changes_df)}")
                print(f"  Price increases: {price_increases}")
                print(f"  Price decreases: {price_decreases}")
                print(f"  Average change: {avg_change:,.0f} NOK ({avg_change_pct:+.1f}%)")
                print()
                
                # Largest changes
                if len(changes_df) > 0:
                    largest_increase = changes_df.nlargest(1, 'change_amount')
                    largest_decrease = changes_df.nsmallest(1, 'change_amount')
                    
                    print("LARGEST CHANGES:")
                    print("-" * 50)
                    if len(largest_increase) > 0:
                        row = largest_increase.iloc[0]
                        print(f"  📈 Largest increase: {row['boat_id']} +{row['change_amount']:,.0f} NOK ({row['change_percent']:+.1f}%)")
                    if len(largest_decrease) > 0:
                        row = largest_decrease.iloc[0]
                        print(f"  📉 Largest decrease: {row['boat_id']} {row['change_amount']:,.0f} NOK ({row['change_percent']:+.1f}%)")
                    print()
            else:
                print("  No price changes recorded yet (all entries are initial prices)")
                print()
            
            # Recent entries
            print("RECENT PRICE UPDATES:")
            print("-" * 50)
            recent = ph_df.tail(10)
            for _, row in recent.iterrows():
                if pd.notna(row['previous_price']):
                    change_sign = "+" if row['change_amount'] >= 0 else ""
                    print(f"  {row['boat_id']}: {row['previous_price']:,.0f} -> {row['price']:,.0f} NOK ({change_sign}{row['change_amount']:,.0f}, {change_sign}{row['change_percent']:.1f}%)")
                else:
                    print(f"  {row['boat_id']}: Initial price {row['price']:,.0f} NOK")
            print()
        else:
            print("No price history data available. Run the scraper multiple times to track changes.")
            print()
    
    print("=" * 70)
    print("VISUALIZATION")
    print("=" * 70)
    
    # Set up visualization
    sns.set_theme(style="whitegrid")
    
    # Check if we have enough data for visualization
    if len(df_clean) < 2:
        print("Not enough data for visualization (need at least 2 listings)")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Top Brands by Count
    top_brands_list = df_clean['Clean_Brand'].value_counts().head(10).index
    df_top = df_clean[df_clean['Clean_Brand'].isin(top_brands_list)]
    
    sns.countplot(
        data=df_top,
        y="Clean_Brand",
        order=top_brands_list,
        hue="Clean_Brand",
        legend=False,
        palette="viridis",
        ax=axes[0, 0],
    )
    axes[0, 0].set_title("Top 10 Most Listed Brands", fontsize=12, weight="bold")
    axes[0, 0].set_xlabel("Number of Listings")
    axes[0, 0].set_ylabel("Brand")
    
    # Plot 2: Price Distribution by Brand
    df_top_copy = df_top.copy()
    df_top_copy["Price (k NOK)"] = df_top_copy["price"] / 1000
    
    sns.boxplot(
        data=df_top_copy,
        x="Price (k NOK)",
        y="Clean_Brand",
        order=top_brands_list,
        hue="Clean_Brand",
        legend=False,
        palette="viridis",
        ax=axes[0, 1],
        showfliers=False,
    )
    axes[0, 1].set_title("Price Range by Brand (Middle 50%)", fontsize=12, weight="bold")
    axes[0, 1].set_xlabel("Price (Thousands NOK)")
    axes[0, 1].set_ylabel("")
    
    # Plot 3: Year Built Distribution
    if len(year_data) > 0:
        year_data_sorted = year_data.sort_values('year_built')
        sns.histplot(
            data=year_data_sorted,
            x="year_built",
            bins=20,
            kde=False,
            ax=axes[1, 0],
            color='royalblue'
        )
        axes[1, 0].set_title("Boat Year Built Distribution", fontsize=12, weight="bold")
        axes[1, 0].set_xlabel("Year Built")
        axes[1, 0].set_ylabel("Count")
    else:
        axes[1, 0].set_visible(False)
    
    # Plot 4: Length Distribution
    if len(length_data) > 0:
        sns.histplot(
            data=length_data,
            x="length",
            bins=15,
            kde=False,
            ax=axes[1, 1],
            color='green'
        )
        axes[1, 1].set_title("Boat Length Distribution", fontsize=12, weight="bold")
        axes[1, 1].set_xlabel("Length (feet)")
        axes[1, 1].set_ylabel("Count")
    else:
        axes[1, 1].set_visible(False)
    
    plt.tight_layout()
    output_img = "finn_boat_market_analysis.png"
    plt.savefig(output_img, dpi=300)
    print(f"\nAnalysis chart successfully saved to {output_img}")
    
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze Finn.no boat listings")
    parser.add_argument("--db-path", default="finn_boats.db", help="Path to SQLite database")
    args = parser.parse_args()
    clean_and_analyze_boats(args.db_path)
