import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def clean_and_analyze_boats(csv_path="finn_sailing_boats_all.csv"):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run the scraper first!")
        return

    # 1. Load data
    df = pd.read_csv(csv_path)

    # 2. Clean up numeric fields and drop rows without valid pricing data
    df["Price (NOK)"] = pd.to_numeric(df["Price (NOK)"], errors="coerce")
    df = df.dropna(subset=["Price (NOK)"])

    # 3. Clean up the 'Brand/Type' column
    # Finn adds ' Seilbåt/Motorseiler' to every brand. Let's clean that for readable charts.
    df["Clean_Brand"] = (
        df["Brand/Type"]
        .astype(str)
        .str.replace(" Seilbåt/Motorseiler", "", case=False, regex=False)
        .str.strip()
    )

    # Filter out empty or 'andre' (others) brands if they clutter the analysis
    df = df[~df["Clean_Brand"].isin(["andre", "nan", "None", ""])]

    print(f"Loaded {len(df)} boat listings with valid pricing data.")

    # 4. Determine the top 10 most common brands listed
    top_brands = df["Clean_Brand"].value_counts().head(10).index
    df_top = df[df["Clean_Brand"].isin(top_brands)]

    # 5. Set up the visualization canvas (2 plots side by side)
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # --- Plot A: Volume Count ---
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

    # --- Plot B: Price Distribution Boxplot ---
    # Convert prices to thousands (k NOK) to keep the axis labels readable
    df_top_copy = df_top.copy()
    df_top_copy["Price (k NOK)"] = df_top_copy["Price (NOK)"] / 1000

    sns.boxplot(
        data=df_top_copy,
        x="Price (k NOK)",
        y="Clean_Brand",
        order=top_brands,
        hue="Clean_Brand",
        legend=False,
        palette="viridis",
        ax=axes[1],
        showfliers=False,  # Hides extreme outliers to keep the visual focused
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
    clean_and_analyze_boats()
