# Streaming Content Explorer

A Streamlit app that combines data from TMDB and OMDB APIs to create a searchable database of streaming content across platforms like Netflix, Apple TV, and more.

## Features

- Search and filter movies and TV shows by title, streaming platform, genre, and IMDb rating
- Visualize content distribution across streaming platforms
- View IMDb ratings and other metadata
- Download complete dataset as CSV

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- Plotly
- Requests

## Setup

1. Clone this repository
2. Install requirements: `pip install -r requirements.txt`
3. Create a `.streamlit/secrets.toml` file with your API keys:
   ```toml
   [api_keys]
   tmdb = "your_tmdb_api_key_here"
   omdb = "your_omdb_api_key_here"
   ```
4. Run the app: `streamlit run app.py`

## Data Sources

- [TMDB API](https://www.themoviedb.org/documentation/api)
- [OMDb API](http://www.omdbapi.com/)

## Deployment

This app can be deployed on Streamlit Cloud.