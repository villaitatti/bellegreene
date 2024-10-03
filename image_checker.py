import csv
import requests
import logging

# Set up logging to a file
logging.basicConfig(filename='missing_images.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def check_image_exists(url):
    try:
        response = requests.head(url)
        print(f"Response code: {response.status_code}\n")
        return response.status_code == 200
    except Exception as e:
        logging.info(f"Error checking URL: {url}. Error: {e}")
        return False

def process_csv(csv_file):
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            iiif_ids = row.get('I Tatti file name(s)', '').split(',')

            for image_id in iiif_ids:
                image_id = image_id.strip()  # Clean up extra spaces
                iiif_url = f"https://iiif.itatti.harvard.edu/iiif/2/bellegreene-full!{image_id}.jpg/full/full/0/default.jpg"
                print(f"Checking image ID: {image_id}")
                if not check_image_exists(iiif_url):
                    logging.info(f"Image not found for ID: {image_id}. URL: {iiif_url}")

if __name__ == "__main__":
    csv_file = 'BG to BB Letters_Spreadsheet - Sheet1.csv'  # Replace with the path to your CSV file
    process_csv(csv_file)