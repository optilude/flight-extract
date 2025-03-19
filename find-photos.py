import flickrapi
import datetime
import requests
import os

# Replace with your Flickr API key and secret
FLICKR_API_KEY = "your_api_key"
FLICKR_API_SECRET = "your_api_secret"

def authenticate_flickr():
    """Authenticate with Flickr and return a Flickr API object."""
    flickr = flickrapi.FlickrAPI(FLICKR_API_KEY, FLICKR_API_SECRET, format='parsed-json')

    if not flickr.token_valid(perms='read'):
        flickr.get_request_token(oauth_callback='oob')
        authorize_url = flickr.auth_url(perms='read')
        print(f"Go to this URL and authorize the app: {authorize_url}")
        
        verifier = input("Enter the verification code: ")
        flickr.get_access_token(verifier)

    return flickr

def search_trip_photos(flickr, start_date, end_date):
    """Search Flickr for photos within a specific date range."""
    
    # Convert dates to Unix timestamps
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

    photos = flickr.photos.search(
        user_id="me",  # Fetch only your photos
        min_taken_date=start_ts,
        max_taken_date=end_ts,
        privacy_filter=2,  # Private photos shared with friends/family
        extras="url_o",  # Get original photo URL
        per_page=500
    )

    return photos["photos"]["photo"]

def download_photos(photo_list, folder):
    """Download photos and save them in the trip folder."""
    if not photo_list:
        print(f"No photos found for {folder}.")
        return

    os.makedirs(folder, exist_ok=True)

    for photo in photo_list:
        url = photo.get("url_o")
        if not url:
            continue  # Skip if no original size URL
        
        photo_id = photo["id"]
        filename = os.path.join(folder, f"{photo_id}.jpg")

        # Download and save the image
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded {filename}")

    print(f"Saved {len(photo_list)} photos to {folder}")

def process_flickr_photos():
    """Fetch photos for each trip and store them in the correct folders."""
    
    flickr = authenticate_flickr()

    with open("flights.csv", "r", encoding="utf-8") as f:
        next(f)  # Skip header
        for line in f:
            data = line.strip().split(",")

            # Extract trip details
            booking_ref, out_date, _, _, _, _, in_date, _, _, _, _ = data
            folder_name = f"{out_date} to {in_date}"

            print(f"Processing trip: {folder_name}")

            # Search and download photos
            photos = search_trip_photos(flickr, out_date, in_date)
            download_photos(photos, folder_name)
