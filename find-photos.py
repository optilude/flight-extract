import json
import argparse
import flickrapi
import datetime
import requests
import os
import csv

import dateutil.parser

def authenticate_flickr():
    """Authenticate with Flickr and return a Flickr API object."""

    config = {}
    with open('flickr.json', 'r') as file:
        config = json.load(file)
    
    api_key = config.get('apiKey')
    api_secret = config.get('apiSecret')

    flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')
    flickr.authenticate_via_browser(perms='read')

    return flickr

def search_photos(flickr, **kwargs):
    """Search for photos on Flickr and return the results."""

    page = 1
    photos = []
    while True:
        response = flickr.photos.search(per_page=500, page=page, **kwargs)
        page_results = response.get('photos', {}).get('photo', [])
        if not page_results:
            break  # No more photos to process
        
        photos.extend(list(page_results))
        page += 1
    
    return photos

def download_photo(photo, folder):
    """Download photos and save them in the trip folder."""

    os.makedirs(folder, exist_ok=True)

    url = photo.get("url_o")
    if not url:
        print(f"No URL found for {photo['id']}")
        return
    
    photo_id = photo["id"]
    photo_format = photo.get('originalformat') or 'jpg'
    filename = os.path.join(folder, f"{photo_id}.{photo_format}")

    # Download and save the image
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded {filename}")

def process_flickr_photos(parent_directory, query, privacy_filter=4, default_length=7):
    """Fetch photos for each trip and store them in the correct folders."""
    
    flickr = authenticate_flickr()
    
    flights_file = os.path.join(parent_directory, "trips.csv")

    with open(flights_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract trip details
            booking_ref = row["Booking Ref"]
            outbound_date = row["Outbound Departure Date"]
            inbound_date = row["Inbound Arrival Date"]

            folder_name = os.path.join(parent_directory, 
                f"{outbound_date} to {inbound_date}" if outbound_date and inbound_date else
                outbound_date or inbound_date
            )

            if not os.path.exists(folder_name):
                print(f"Trip folder not found: {folder_name}")
                continue

            print(f"Processing trip: {folder_name}")

            start_date = dateutil.parser.parse(outbound_date) if outbound_date else None
            end_date = dateutil.parser.parse(inbound_date) if inbound_date else start_date + datetime.timedelta(days=default_length)

            # Search and download photos
            photos = search_photos(flickr,
                user_id="me",
                text=query,
                min_taken_date=start_date.strftime("%Y-%m-%d"),
                max_taken_date=end_date.strftime("%Y-%m-%d"),
                privacy_filter=privacy_filter,
                extras="original_format,url_o",
            )
        
            print(f"Found {len(photos)} photos for trip {folder_name}")
            for photo in photos:
                download_photo(photo, folder_name)


def main():
    """Main function to find photos for flights."""
    parser = argparse.ArgumentParser(description="Find photos matching flights.")
    parser.add_argument(
        '--parent-directory', 
        type=str, 
        default='trips', 
        help="Parent directory containing trips (default: 'trips')"
    )
    parser.add_argument(
        '--query', 
        type=str, 
        default=None, 
        help="Additional Flickr query text"
    )
    parser.add_argument(
        '--privacy-filter', 
        type=int, 
        default=None, 
        help="Privacy filter to restrict to"
    )
    parser.add_argument(
        '--default-trip-length', 
        type=int, 
        default=7, 
        help="Number of days to search if inbound date is missing (default: 7)"
    )
    args = parser.parse_args()

    parent_directory = args.parent_directory
    query = args.query
    privacy_filter = args.privacy_filter

    process_flickr_photos(parent_directory, query, privacy_filter)

if __name__ == '__main__':
    main()


