import streamlit as st
import pandas as pd
import os
import time
import plotly.express as px
from data_fetcher import load_or_create_database

# Page configuration
st.set_page_config(page_title="Streaming Content Explorer", layout="wide")

# Sidebar for API keys and settings
with st.sidebar:
    st.title("Settings")
    
    # API keys input (store in session state)
    if "tmdb_api_key" not in st.session_state:
        st.session_state.tmdb_api_key = ""
    if "omdb_api_key" not in st.session_state:
        st.session_state.omdb_api_key = ""
    
    tmdb_api_key = st.text_input("TMDB API Key", value=st.session_state.tmdb_api_key, type="password")
    omdb_api_key = st.text_input("OMDB API Key", value=st.session_state.omdb_api_key, type="password")
    
    # Update session state
    st.session_state.tmdb_api_key = tmdb_api_key
    st.session_state.omdb_api_key = omdb_api_key
    
    # Database options
    max_pages = st.slider("Max Pages per Provider", min_value=1, max_value=10, value=2,
                         help="Higher values give more results but take longer to fetch")
    
    force_refresh = st.checkbox("Force Refresh Database", value=False,
                               help="Check to rebuild the database even if one exists")
    
    refresh_button = st.button("Refresh Database")
    
    st.divider()
    
    # About section
    st.subheader("About")
    st.markdown("""
    This app combines data from TMDB and OMDB APIs to create a searchable database of streaming content.
    
    You need API keys from:
    - [TMDB](https://www.themoviedb.org/settings/api)
    - [OMDB](http://www.omdbapi.com/apikey.aspx)
    
    Data includes:
    - Movies and TV shows
    - Streaming platforms
    - Genres
    - IMDb ratings
    """)

# Main content
st.title("Streaming Content Explorer")

# Function to display progress
def update_progress(message, progress):
    progress_bar.progress(progress)
    status_text.text(message)

# Check if we need to load or create the database
if "df" not in st.session_state or refresh_button:
    if not tmdb_api_key or not omdb_api_key:
        st.warning("Please enter your TMDB and OMDB API keys in the sidebar.")
        st.stop()
    
    # Setup progress indicators
    st.subheader("Loading Data...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Load or create database
    try:
        df, filename = load_or_create_database(
            tmdb_api_key, 
            omdb_api_key, 
            force_refresh=force_refresh,
            max_pages=max_pages,
            progress_callback=update_progress
        )
        st.session_state.df = df
        st.session_state.filename = filename
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        st.success(f"Database loaded successfully: {filename} with {len(df)} entries")
        time.sleep(1)
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Error loading database: {e}")
        st.stop()
else:
    df = st.session_state.df
    filename = st.session_state.filename if "filename" in st.session_state else "Unknown"

# Once data is loaded, show the app
st.write(f"Database: {filename} | Total entries: {len(df)}")

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["Search & Filter", "Visualizations", "Raw Data"])

with tab1:
    # Search and filter section
    col1, col2 = st.columns(2)
    
    with col1:
        # Text search
        search_term = st.text_input("Search by Title", "")
        
        # Content type
        content_type = st.multiselect(
            "Content Type",
            options=sorted(df["type"].unique()),
            default=sorted(df["type"].unique())
        )
    
    streaming_providers_default = [
    'Apple TV',
    'Netflix'
    ]
    with col2:
        # Streaming providers
        providers = st.multiselect(
            "Streaming Providers",
            options=sorted(df["provider"].unique()),
            # default=sorted(df["provider"].unique())
            default = streaming_providers_default
        )
        
        # IMDb rating range
        # Convert to numeric, replacing non-numeric values with NaN
        df["imdb_rating_num"] = pd.to_numeric(df["imdb_rating"], errors="coerce")
        
        min_rating, max_rating = float(df["imdb_rating_num"].min()), float(df["imdb_rating_num"].max())
        rating_range = st.slider(
            "IMDb Rating Range",
            min_value=min_rating,
            max_value=max_rating,
            value=(min_rating, max_rating),
            step=0.1
        )
    
    # Genre selection
    # Extract all unique genres
    all_genres = set()
    for genres_str in df["genres"].dropna():
        genres = [g.strip() for g in genres_str.split(",")]
        all_genres.update(genres)
    
    selected_genres = st.multiselect(
        "Select Genres",
        options=sorted(all_genres),
        default=['Family']
    )
    
    # Apply filters
    filtered_df = df.copy()
    
    # Text search
    if search_term:
        filtered_df = filtered_df[filtered_df["title"].str.contains(search_term, case=False, na=False)]
    
    # Content type
    if content_type:
        filtered_df = filtered_df[filtered_df["type"].isin(content_type)]
    
    # Providers
    if providers:
        filtered_df = filtered_df[filtered_df["provider"].isin(providers)]
    
    # IMDb rating
    filtered_df = filtered_df[
        (filtered_df["imdb_rating_num"] >= rating_range[0]) & 
        (filtered_df["imdb_rating_num"] <= rating_range[1])
    ]
    
    # Genres (match if any selected genre is in the genres list)
    if selected_genres:
        genre_mask = filtered_df["genres"].apply(
            lambda x: any(genre in str(x).split(", ") for genre in selected_genres) if pd.notna(x) else False
        )
        filtered_df = filtered_df[genre_mask]
    
    # Display results
    st.subheader(f"Results: {len(filtered_df)} items")
    
    # Sort options
    sort_options = {
        "IMDb Rating (High to Low)": ("imdb_rating_num", False),
        "IMDb Rating (Low to High)": ("imdb_rating_num", True),
        "Title (A-Z)": ("title", True),
        "Title (Z-A)": ("title", False),
        "Release Date (Newest First)": ("release_date", False),
        "Release Date (Oldest First)": ("release_date", True),
    }
    
    sort_by = st.selectbox("Sort by", options=list(sort_options.keys()))
    sort_col, sort_asc = sort_options[sort_by]
    
    filtered_df = filtered_df.sort_values(by=sort_col, ascending=sort_asc)
    
    # Display as cards in a grid
    cols = st.columns(3)
    
    for i, (_, row) in enumerate(filtered_df.iterrows()):
        col_idx = i % 3
        
        with cols[col_idx]:
            st.markdown("---")
            
            # Create card with poster if available
            if pd.notna(row["poster_path"]):
                poster_url = f"https://image.tmdb.org/t/p/w200{row['poster_path']}"
                st.image(poster_url, width=150)
            
            st.subheader(row["title"])
            st.write(f"**Type:** {row['type']} | **Provider:** {row['provider']}")
            
            if pd.notna(row["imdb_rating"]) and row["imdb_rating"] != "N/A":
                st.write(f"**IMDb Rating:** ⭐ {row['imdb_rating']}/10")
            else:
                st.write("**IMDb Rating:** Not available")
                
            if pd.notna(row["genres"]):
                st.write(f"**Genres:** {row['genres']}")
                
            if pd.notna(row["release_date"]):
                st.write(f"**Released:** {row['release_date']}")
                
            if pd.notna(row["overview"]):
                st.write(row["overview"][:150] + "..." if len(row["overview"]) > 150 else row["overview"])
                
            # Links to more information
            if pd.notna(row["imdb_id"]):
                st.markdown(f"[View on IMDb](https://www.imdb.com/title/{row['imdb_id']})")

with tab2:
    # Visualizations
    st.subheader("Data Visualizations")
    
    viz_type = st.selectbox(
        "Select Visualization",
        options=[
            "Content Distribution by Provider",
            "Average IMDb Rating by Provider",
            "Content by Genre",
            "Rating Distribution"
        ]
    )
    
    if viz_type == "Content Distribution by Provider":
        # Count of content by provider
        provider_counts = df["provider"].value_counts().reset_index()
        provider_counts.columns = ["Provider", "Count"]
        
        fig = px.pie(
            provider_counts, 
            values="Count", 
            names="Provider",
            title="Content Distribution by Streaming Provider"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    elif viz_type == "Average IMDb Rating by Provider":
        # Average rating by provider
        avg_ratings = df.groupby("provider")["imdb_rating_num"].mean().reset_index()
        avg_ratings.columns = ["Provider", "Average IMDb Rating"]
        avg_ratings = avg_ratings.sort_values("Average IMDb Rating", ascending=False)
        
        fig = px.bar(
            avg_ratings,
            x="Provider",
            y="Average IMDb Rating",
            title="Average IMDb Rating by Provider",
            labels={"Average IMDb Rating": "Average Rating (out of 10)"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
    elif viz_type == "Content by Genre":
        # Count by genre (explode the genres)
        genre_data = []
        for _, row in df.iterrows():
            if pd.notna(row["genres"]):
                for genre in row["genres"].split(", "):
                    genre_data.append({
                        "Genre": genre.strip(),
                        "Type": row["type"]
                    })
        
        genre_df = pd.DataFrame(genre_data)
        genre_counts = genre_df.groupby(["Genre", "Type"]).size().reset_index(name="Count")
        
        fig = px.bar(
            genre_counts,
            x="Genre",
            y="Count",
            color="Type",
            title="Content Distribution by Genre and Type",
            labels={"Count": "Number of Titles"}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
    elif viz_type == "Rating Distribution":
        # Distribution of IMDb ratings
        fig = px.histogram(
            df[df["imdb_rating_num"].notna()],
            x="imdb_rating_num",
            nbins=20,
            title="Distribution of IMDb Ratings",
            labels={"imdb_rating_num": "IMDb Rating"}
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    # Raw data view
    st.subheader("Raw Data")
    st.dataframe(df)
    
    # Download option
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Data as CSV",
        csv_data,
        "streaming_content_data.csv",
        "text/csv",
        key='download-csv'
    )