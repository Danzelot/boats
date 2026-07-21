import os
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# --- Configuration ---
st.set_page_config(
    page_title="Finn.no Boat Explorer",
    page_icon="⛵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {font-size: 3rem; font-weight: bold; color: #1f77b4;}
    .metric-card {background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 0.5rem; margin-bottom: 1rem;}
    </style>
    """, unsafe_allow_html=True)


# --- Data Loading ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data(db_path="finn_boats.db"):
    """Load boat data from SQLite database."""
    if not os.path.exists(db_path):
        st.error(f"Database {db_path} not found. Run the scraper first with --scrape-details!")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM boats WHERE price IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Data cleaning
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    
    # Extract boat type clean name
    # Use 'type' column if it exists, otherwise 'boat_type'
    type_col = "type" if "type" in df.columns else "boat_type"
    df["type_clean"] = df[type_col].fillna("").str.replace("Seilbåt/Motorseiler", "Sailboat").str.strip()
    
    # Calculate age
    current_year = pd.Timestamp.now().year
    if "year_built" in df.columns:
        df["age"] = current_year - df["year_built"]
    else:
        df["age"] = None
    
    return df


# --- Main App ---
def main():
    st.markdown('<p class="main-header">⛵ Finn.no Sailing Boat Explorer</p>', unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    
    if df.empty:
        st.warning("No data loaded. Please run the scraper with --scrape-details first.")
        return

    # --- Sidebar Filters ---
    st.sidebar.header("🔍 Filters")

    # Price range
    min_price = float(df["price"].min())
    max_price = float(df["price"].max())
    price_range = st.sidebar.slider(
        "Price Range (NOK)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price),
        format="%,.0f"
    )

    # Length range
    if "length" in df.columns and df["length"].notna().any():
        min_length = float(df["length"].min())
        max_length = float(df["length"].max())
        length_range = st.sidebar.slider(
            "Length Range (feet)",
            min_value=min_length,
            max_value=max_length,
            value=(min_length, max_length),
            step=1.0
        )
    else:
        length_range = (0, 100)

    # Age range
    if "age" in df.columns and df["age"].notna().any():
        min_age = int(df["age"].min())
        max_age = int(df["age"].max())
        age_range = st.sidebar.slider(
            "Age Range (years)",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age)
        )
    else:
        age_range = (0, 50)

    # Brand filter
    brands = ["All"]
    if "brand" in df.columns:
        brands += sorted([b for b in df["brand"].dropna().unique() if b and b.strip() and b != "Andre"])
    selected_brand = st.sidebar.selectbox("Brand", brands)

    # Boat type filter
    boat_types = ["All"]
    if "type_clean" in df.columns:
        boat_types += sorted([t for t in df["type_clean"].dropna().unique() if t and t.strip()])
    selected_type = st.sidebar.selectbox("Boat Type", boat_types)

    # Material filter
    materials = ["All"]
    if "material" in df.columns:
        materials += sorted([m for m in df["material"].dropna().unique() if m and m.strip()])
    selected_material = st.sidebar.selectbox("Material", materials)

    # Equipment keyword filter
    equipment_keyword = st.sidebar.text_input("Equipment Keyword", "")

    # Fuel type filter
    fuel_types = ["All"]
    if "fuel_type" in df.columns:
        fuel_types += sorted([f for f in df["fuel_type"].dropna().unique() if f and f.strip()])
    selected_fuel = st.sidebar.selectbox("Fuel Type", fuel_types)

    # Location filter
    locations = ["All"]
    if "location" in df.columns:
        locations += sorted([l for l in df["location"].dropna().unique() if l and l.strip()])
    selected_location = st.sidebar.selectbox("Location", locations)

    # --- Apply Filters ---
    filtered_df = df.copy()

    # Apply filters
    filtered_df = filtered_df[
        (filtered_df["price"] >= price_range[0]) &
        (filtered_df["price"] <= price_range[1])
    ]

    if "length" in filtered_df.columns and filtered_df["length"].notna().any():
        filtered_df = filtered_df[
            (filtered_df["length"].isna()) |
            ((filtered_df["length"] >= length_range[0]) & (filtered_df["length"] <= length_range[1]))
        ]

    if "age" in filtered_df.columns and filtered_df["age"].notna().any():
        filtered_df = filtered_df[
            (filtered_df["age"].isna()) |
            ((filtered_df["age"] >= age_range[0]) & (filtered_df["age"] <= age_range[1]))
        ]

    if selected_brand != "All" and "brand" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["brand"] == selected_brand]

    if selected_type != "All" and "type_clean" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["type_clean"] == selected_type]

    if selected_material != "All" and "material" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["material"] == selected_material]

    if selected_fuel != "All" and "fuel_type" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["fuel_type"] == selected_fuel]

    if selected_location != "All" and "location" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["location"] == selected_location]

    if equipment_keyword and "equipment" in filtered_df.columns:
        equipment_mask = filtered_df["equipment"].fillna("").str.contains(
            equipment_keyword, case=False, na=False
        )
        filtered_df = filtered_df[equipment_mask]

    # --- Statistics in Sidebar ---
    st.sidebar.markdown("---")
    st.sidebar.metric("Total Listings", len(df))
    st.sidebar.metric("Filtered Results", len(filtered_df))
    
    if len(filtered_df) == 0:
        st.warning("No results match your filters. Try adjusting the criteria.")
        return

    # --- Main Dashboard ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "📈 Price Analysis", 
        "🔬 Deep Dive",
        "📋 Listings"
    ])

    # TAB 1: Overview
    with tab1:
        st.header("Market Overview")

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Price", f"{filtered_df['price'].mean():,.0f} NOK")
        with col2:
            st.metric("Price Range", f"{filtered_df['price'].min():,.0f} - {filtered_df['price'].max():,.0f} NOK")
        with col3:
            if "age" in filtered_df.columns and filtered_df["age"].notna().any():
                avg_age = filtered_df["age"].mean()
                st.metric("Avg Age", f"{avg_age:.0f} years")
            else:
                st.metric("Avg Age", "N/A")
        with col4:
            if filtered_df["length"].notna().any():
                avg_length = filtered_df["length"].mean()
                st.metric("Avg Length", f"{avg_length:.1f} ft")
            else:
                st.metric("Avg Length", "N/A")

        # Top brands chart
        st.subheader("Top Brands by Count")
        brand_counts = filtered_df["brand"].value_counts().head(10)
        if len(brand_counts) > 0:
            fig = px.bar(
                x=brand_counts.values,
                y=brand_counts.index,
                orientation='h',
                title="Number of Listings by Brand",
                labels={'x': 'Count', 'y': 'Brand'},
                color=brand_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No brand data available")

        # Price distribution overview
        st.subheader("Price Distribution")
        fig = px.histogram(
            filtered_df,
            x="price",
            nbins=30,
            title="Price Distribution Histogram",
            labels={"price": "Price (NOK)", "count": "Frequency"},
            marginal="box"
        )
        st.plotly_chart(fig, use_container_width=True)

    # TAB 2: Price Analysis
    with tab2:
        st.header("Price Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Price vs Length scatter
            st.subheader("Price vs Length")
            length_df = filtered_df.dropna(subset=["length"])
            if len(length_df) > 0:
                fig = px.scatter(
                    length_df,
                    x="length",
                    y="price",
                    color="brand",
                    size="age",
                    hover_data=["model", "year_built", "location"],
                    title="Price by Length and Age",
                    labels={
                        "length": "Length (feet)",
                        "price": "Price (NOK)",
                        "age": "Age (years)"
                    }
                )
                fig.update_traces(marker=dict(line=dict(width=0.5, color='white')))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No length data available for scatter plot")

        with col2:
            # Price vs Age scatter
            st.subheader("Price vs Age")
            age_df = filtered_df.dropna(subset=["age"])
            if len(age_df) > 0 and "age" in age_df.columns:
                fig = px.scatter(
                    age_df,
                    x="age",
                    y="price",
                    color="brand",
                    hover_data=["model", "year_built", "length"],
                    title="Price by Age",
                    labels={
                        "age": "Age (years)",
                        "price": "Price (NOK)"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No age data available for scatter plot")

        # Price by Brand box plot
        st.subheader("Price Distribution by Brand")
        brand_df = filtered_df[filtered_df["brand"].notna()]
        if len(brand_df) > 0:
            top_brands = brand_df["brand"].value_counts().head(8).index
            brand_df_top = brand_df[brand_df["brand"].isin(top_brands)]

            fig = px.box(
                brand_df_top,
                x="brand",
                y="price",
                title="Price Range by Brand (Top 8)",
                labels={"price": "Price (NOK)", "brand": "Brand"},
                color="brand"
            )
            fig.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        # Length vs Price with trendline
        st.subheader("Length vs Price Relationship")
        length_df = filtered_df.dropna(subset=["length"])
        if len(length_df) > 5:
            fig = px.scatter(
                length_df,
                x="length",
                y="price",
                trendline="ols",
                title="Price Trend by Length",
                labels={"length": "Length (feet)", "price": "Price (NOK)"},
                trendline_color_override="red"
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 3: Deep Dive
    with tab3:
        st.header("Deep Dive Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Correlation heatmap
            st.subheader("Correlation Matrix")
            numeric_cols = ["price", "length", "year_built", "age"]
            # Only include columns that exist and have data
            available_numeric = [c for c in numeric_cols if c in filtered_df.columns and filtered_df[c].notna().any()]
            if len(available_numeric) > 1:
                corr_df = filtered_df[available_numeric].dropna()
                if len(corr_df) > 1:
                    corr_matrix = corr_df.corr()
                    fig = px.imshow(
                        corr_matrix,
                        text_auto='.2f',
                        aspect='auto',
                        color_continuous_scale='RdBu_r',
                        title="Feature Correlations"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough numeric data for correlation")
            else:
                st.info("Not enough numeric data for correlation")

            # Material distribution
            st.subheader("Boat Materials")
            if filtered_df["material"].notna().any():
                material_counts = filtered_df["material"].value_counts()
                fig = px.pie(
                    values=material_counts.values,
                    names=material_counts.index,
                    title="Material Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No material data available")

        with col2:
            # Year built distribution
            st.subheader("Year Built Distribution")
            if "year_built" in filtered_df.columns and filtered_df["year_built"].notna().any():
                fig = px.histogram(
                    filtered_df,
                    x="year_built",
                    nbins=20,
                    title="Boats by Year Built",
                    labels={"year_built": "Year", "count": "Count"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No year data available")

            # Engine manufacturer distribution
            st.subheader("Engine Manufacturers")
            if filtered_df["engine_manufacturer"].notna().any():
                engine_counts = filtered_df["engine_manufacturer"].value_counts().head(10)
                fig = px.bar(
                    x=engine_counts.index,
                    y=engine_counts.values,
                    title="Top Engine Manufacturers",
                    labels={"x": "Manufacturer", "y": "Count"}
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No engine data available")

        # Equipment analysis
        st.subheader("Equipment Analysis")
        equipment_df = filtered_df[filtered_df["equipment"].notna()]
        if len(equipment_df) > 0:
            st.info("💡 **Tip:** Use the sidebar 'Equipment Keyword' filter to search for specific equipment")

            # Most common equipment mentions
            all_equipment = " ".join(equipment_df["equipment"].astype(str))
            words = all_equipment.lower().split()
            # Filter out very common words
            stop_words = {'og', 'i', 'på', 'til', 'med', 'av', 'for', 'er', 'som', 'en', 'et', 'den', 'de'}
            words = [w for w in words if w not in stop_words and len(w) > 2]
            word_counts = pd.Series(words).value_counts().head(20)
            
            if len(word_counts) > 0:
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = px.bar(
                        x=word_counts.values,
                        y=word_counts.index,
                        orientation='h',
                        title="Most Mentioned Equipment Terms",
                        labels={"x": "Frequency", "y": "Term"}
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.metric("Unique Terms", len(word_counts))
                    st.dataframe(word_counts.head(10).reset_index(), height=300, use_container_width=True)

    # TAB 4: Listings
    with tab4:
        st.header("Matching Listings")

        # Sort options
        col1, col2, col3 = st.columns(3)
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                ["price", "year_built", "length", "age"],
                index=0
            )
        with col2:
            sort_order = st.radio("Order", ["Ascending", "Descending"], horizontal=True)
        with col3:
            items_per_page = st.selectbox("Items per page", [10, 25, 50, 100], index=1)

        # Sort dataframe
        ascending = (sort_order == "Ascending")
        sorted_df = filtered_df.sort_values(
            by=sort_by,
            ascending=ascending,
            na_position='last'
        )

        # Pagination
        total_items = len(sorted_df)
        total_pages = (total_items - 1) // items_per_page + 1
        
        page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, step=1)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        page_df = sorted_df.iloc[start_idx:end_idx]

        # Display options
        col1, col2 = st.columns(2)
        with col1:
            show_images = st.checkbox("Show images", value=True)
        with col2:
            show_description = st.checkbox("Show full description", value=False)

        st.markdown(f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} results")
        
        # Display listings
        for idx, row in page_df.iterrows():
            # Safely get values with defaults
            brand = row.get('brand', 'N/A') or 'N/A'
            model = row.get('model', '') or ''
            price = row.get('price', 0) or 0
            year_built = row.get('year_built')
            
            expander_title = f"📌 {brand} {model} - {price:,.0f} NOK"
            if pd.notna(year_built):
                expander_title += f" - {int(year_built)}"
            else:
                expander_title += " - N/A"
            
            with st.expander(expander_title):
                col1, col2 = st.columns([2, 1])

                with col1:
                    if row.get('title'):
                        st.markdown(f"**{row['title']}**")
                    
                    details = []
                    if pd.notna(row.get('year_built')):
                        details.append(f"📅 Year: {int(row['year_built'])}")
                    if pd.notna(row.get('length')):
                        details.append(f"📏 Length: {row['length']:.1f} ft")
                    if row.get('location'):
                        details.append(f"📍 Location: {row['location']}")
                    if row.get('material'):
                        details.append(f"🏗️ Material: {row['material']}")
                    if row.get('engine_manufacturer') and row.get('engine_size'):
                        details.append(f"⚙️ Engine: {row['engine_manufacturer']} {row['engine_size']}")
                    if row.get('fuel_type'):
                        details.append(f"⛽ Fuel: {row['fuel_type']}")
                    if row.get('color'):
                        details.append(f"🎨 Color: {row['color']}")
                    
                    if details:
                        st.markdown(" | ".join(details))
                    
                    if show_description and row.get('description'):
                        st.markdown("**Description:**")
                        st.write(row['description'])

                    if show_description and row.get('equipment'):
                        st.markdown("**Equipment:**")
                        st.write(row['equipment'])

                with col2:
                    if show_images and row.get('image'):
                        try:
                            st.image(row['image'], use_container_width=True)
                        except:
                            st.warning("Could not load image")
                    
                    if row.get('url'):
                        st.markdown(f"[View on Finn.no]({row['url']})")
                    
                    if row.get('finn_code'):
                        st.caption(f"FINN Code: {row['finn_code']}")
                    if row.get('date_updated'):
                        st.caption(f"Updated: {row['date_updated']}")

    # --- Footer ---
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 2rem;'>
            <p>Data from Finn.no | Built with Python & Streamlit</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
