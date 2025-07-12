import requests
import pandas as pd
import time
import os
from datetime import datetime

class StreamingDataFetcher:
    def __init__(self, tmdb_api_key, omdb_api_key, region="US"):
        self.tmdb_api_key = tmdb_api_key
        self.omdb_api_key = omdb_api_key
        self.region = region
        self.providers = {
            8: "Netflix",
            2: "Apple TV",
            9: "Amazon Prime",
            337: "Disney+",
            384: "HBO Max",
            15: "Hulu",
            # Add more as needed
        }
        
    def get_streaming_content(self, content_type="movie", provider_id=8, page=1):
        """Get content (movies or TV shows) from a specific streaming provider."""
        url = f"https://api.themoviedb.org/3/discover/{content_type}"
        params = {
            "api_key": self.tmdb_api_key,
            "with_watch_providers": provider_id,
            "watch_region": self.region,
            "page": page
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_imdb_data(self, imdb_id):
        """Get IMDb rating and additional data from OMDb API."""
        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={self.omdb_api_key}"
        response = requests.get(url)
        return response.json()

    def get_external_ids(self, content_type, tmdb_id):
        """Get external IDs including IMDb ID for a movie or TV show."""
        url = f"https://api.themoviedb.org/3/{content_type}/{tmdb_id}/external_ids"
        params = {"api_key": self.tmdb_api_key}
        response = requests.get(url, params=params)
        return response.json()

    def get_content_details(self, content_type, tmdb_id):
        """Get detailed information about a movie or TV show."""
        url = f"https://api.themoviedb.org/3/{content_type}/{tmdb_id}"
        params = {"api_key": self.tmdb_api_key}
        response = requests.get(url, params=params)
        return response.json()

    def build_content_database(self, max_pages=2, progress_callback=None):
        """Build a comprehensive database of streaming content with progress callback."""
        all_content = []
        total_providers = len(self.providers)
        content_types = ["movie", "tv"]
        
        provider_idx = 0
        for content_type in content_types:
            for provider_id, provider_name in self.providers.items():
                provider_idx += 1
                
                # Get first page to determine total pages
                try:
                    initial_data = self.get_streaming_content(content_type, provider_id)
                    total_pages = min(initial_data.get("total_pages", 1), max_pages)
                    
                    for page in range(1, total_pages + 1):
                        if progress_callback:
                            progress_message = f"Processing {provider_name} {content_type}s - page {page}/{total_pages}"
                            overall_progress = (provider_idx - 1) / total_providers
                            progress_callback(progress_message, overall_progress)
                        
                        if page > 1:  # Skip first page as we already have it
                            data = self.get_streaming_content(content_type, provider_id, page)
                        else:
                            data = initial_data
                        
                        for item in data.get("results", []):
                            try:
                                tmdb_id = item["id"]
                                
                                # Get more details about the content
                                details = self.get_content_details(content_type, tmdb_id)
                                
                                # Get external IDs to find IMDb ID
                                external_ids = self.get_external_ids(content_type, tmdb_id)
                                imdb_id = external_ids.get("imdb_id")
                                
                                # Basic content info
                                content_info = {
                                    "type": "TV Show" if content_type == "tv" else "Movie",
                                    "title": item.get("name") if content_type == "tv" else item.get("title"),
                                    "overview": item.get("overview"),
                                    "tmdb_id": tmdb_id,
                                    "imdb_id": imdb_id,
                                    "provider": provider_name,
                                    "release_date": item.get("first_air_date" if content_type == "tv" else "release_date"),
                                    "tmdb_rating": item.get("vote_average"),
                                    "popularity": item.get("popularity"),
                                    "poster_path": item.get("poster_path"),
                                }
                                
                                # Add genres
                                if "genres" in details:
                                    content_info["genres"] = ", ".join([genre["name"] for genre in details["genres"]])
                                
                                # Get IMDb rating if IMDb ID is available
                                if imdb_id:
                                    imdb_data = self.get_imdb_data(imdb_id)
                                    content_info["imdb_rating"] = imdb_data.get("imdbRating", "N/A")
                                    content_info["imdb_votes"] = imdb_data.get("imdbVotes", "N/A")
                                else:
                                    content_info["imdb_rating"] = "N/A"
                                    content_info["imdb_votes"] = "N/A"
                                
                                all_content.append(content_info)
                            except Exception as e:
                                print(f"Error processing item: {e}")
                            
                            # Sleep to avoid hitting API rate limits
                            time.sleep(0.5)
                        
                        # Sleep between pages
                        time.sleep(1)
                except Exception as e:
                    print(f"Error processing {provider_name} {content_type}: {e}")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_content)
        
        # Save to CSV with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"streaming_content_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        return df, filename

def load_or_create_database(tmdb_api_key, omdb_api_key, force_refresh=False, max_pages=2, progress_callback=None):
    """Load existing database or create a new one if needed."""
    # Look for existing CSV files
    csv_files = [f for f in os.listdir() if f.startswith("streaming_content_") and f.endswith(".csv")]
    
    if csv_files and not force_refresh:
        # Use the most recent file
        latest_file = sorted(csv_files)[-1]
        return pd.read_csv(latest_file), latest_file
    else:
        # Create a new database
        fetcher = StreamingDataFetcher(tmdb_api_key, omdb_api_key)
        return fetcher.build_content_database(max_pages, progress_callback)