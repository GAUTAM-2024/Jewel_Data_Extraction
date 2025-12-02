import os
import re
import requests
from bs4 import BeautifulSoup

# Path to your HTML file
HTML_FILE = os.path.join(os.path.dirname(__file__), 'ref_img_element.html')
# Output directory for images
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'downloaded_images_limelight')

# Supported image extensions
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']

def extract_img_links_from_limelight(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    ul = soup.find('ul', class_='product__media-list')
    if not ul:
        print('No product__media-list found!')
        return []
    img_tags = ul.find_all('img')
    links = []
    for img in img_tags:
        src = img.get('src')
        if src:
            # Find the first supported extension in the src
            match = re.search(r'(https?:)?//[^\s"']+?(' + '|'.join([re.escape(ext) for ext in IMAGE_EXTENSIONS]) + r')', src, re.IGNORECASE))
            if match:
                url = match.group(0)
                if url.startswith('//'):
                    url = 'https:' + url
                links.append(url)
    return links

def download_images(links, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for idx, url in enumerate(links, 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            filename = f"image_{idx}.jpg"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {url} -> {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def main():
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    links = extract_img_links_from_limelight(html_content)
    print(f"Found {len(links)} image links.")
    download_images(links, OUTPUT_DIR)

if __name__ == '__main__':
    main()
