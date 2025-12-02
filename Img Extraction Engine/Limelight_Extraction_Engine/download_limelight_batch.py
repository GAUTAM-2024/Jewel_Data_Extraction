import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Path to your Excel file
EXCEL_FILE = 'LimeLight.xlsx'  # Change if your file is named differently
# Output directory for all products
OUTPUT_ROOT = 'downloaded_limelight_products'

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']


def extract_img_links_from_limelight(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    ul = soup.find('ul', class_='product__media-list')
    # print(ul)
    if not ul:
        return []
    img_tags = ul.find_all('img')
    links = []
    for img in img_tags:
        src = img.get('src')
        if src:
            # Regex: match up to extension, include query params, escape single quote
            match = re.search(r'(https?:)?//[^\s"\']+?(' + '|'.join([re.escape(ext) for ext in IMAGE_EXTENSIONS]) + r')(?:\?[^"\']*)?', src, re.IGNORECASE)
            if match:
                url = match.group(0)
                if url.startswith('//'):
                    url = 'https:' + url
                links.append(url)
    return links

def download_images(links, output_dir, product_id):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for idx, url in enumerate(links, 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            filename = f"{product_id}_{idx}.jpg"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {url} -> {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def main():
    df = pd.read_excel(EXCEL_FILE)
    for _, row in df.iterrows():
        product_id = row['Product_Id']
        url = row['Source Link']
        print(f"Processing Product {product_id} from {url}")
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            links = extract_img_links_from_limelight(resp.text)
            print(f"  Found {len(links)} images.")
            product_dir = os.path.join(OUTPUT_ROOT, str(product_id))
            download_images(links, product_dir, product_id)
        except Exception as e:
            print(f"  Failed to process {url}: {e}")

if __name__ == '__main__':
    main()
