import os
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def get_db_connection(db_path="finn_boats.db"):
    """Get connection to SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Run the scraper first!")
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
    
    # Clean up numeric fields and drop rows without valid pricing data
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    
    # Clean up the 'brand' column
    df["Clean_Brand"] = (
        df["brand"]
        .astype(str)
        .str.replace(" Seilb\u00e5t/Motorseiler", "", case=False, regex=False)
        .str.replace(" Seilb\u00e5t", "", case=False, regex=False)
        .str.strip()
    )
    
    # Filter out empty or 'andre' brands
    df = df[~df["Clean_Brand"].isin(["andre", "nan", "None", ""])]
    
    print(f"Loaded {len(df)} boat listings with valid pricing data.")
    
    # Determine top 10 brands
    top_brands = df["Clean_Brand"].value_counts().head(10).index
    df_top = df[df["Clean_Brand"].isin(top_brands)]
    
    # Set up visualization
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # Plot A: Volume Count
    sns.countplot(
        data=df_top,
        y="Clean_Brand",
        order=top_brands,
        hue="Clean_Brand",
        legend=False,
        palette="viridis",
        ax=axes[0],
    )
    axes[0].set_title(
        "Top 10 Most Listed Sailing Boat Brands on Finn.no",
        fontsize=14,
        weight="bold",
    )
    axes[0].set_xlabel("Number of Listings Available")
    axes[0].set_ylabel("Brand")
    
    # Plot B: Price Distribution
    df_top_copy = df_top.copy()
    df_top_copy["Price (k NOK)"] = df_top_copy["price"] / 1000
    
    sns.boxplot(
        data=df_top_copy,
        x="Price (k NOK)",
        y="Clean_Brand",
        order=top_brands,
        hue="Clean_Brand",
        legend=False,
        palette="viridis",
        ax=axes[1],
        showfliers=False,
    )
    axes[1].set_title(
        "Market Price Range by Brand (Middle 50% spread)",
        fontsize=14,
        weight="bold",
    )
    axes[1].set_xlabel("Price (Thousands NOK)")
    axes[1].set_ylabel("")  # Hide label since it shares the axis with Plot A
    
    # Tighten layout framework & render to screen
    plt.tight_layout()
    
    # Save to disk
    output_img = "finn_boat_market_analysis.png"
    plt.savefig(output_img, dpi=300)
    print(f"Analysis chart successfully saved to {output_img}")
    
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze Finn.no boat listings")
    parser.add_argument("--db-path", default="finn_boats.db", help="Path to SQLite database")
    args = parser.parse_args()
    clean_and_analyze_boats(args.db_path)
