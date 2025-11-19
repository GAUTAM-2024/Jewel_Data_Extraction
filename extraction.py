import requests
from bs4 import BeautifulSoup
import os

url = "https://ivanajewels.com/products/0-75-carat-lab-grown-diamond-studs"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# Find the Product-Slider section by id
product_slider = soup.find(id="Product-Slider")
print(product_slider)
# Extract all image URLs from Product-Slider
image_urls = []
if product_slider:
    for img in product_slider.find_all("img"):
        # Get the src attribute and make sure it's a full URL
        src = img.get("src")
        if src:
            if src.startswith("//"):
                src = "https:" + src
            image_urls.append(src)
        # Optionally, get all srcset images
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                url_part = part.strip().split(" ")[0]
                if url_part.startswith("//"):
                    url_part = "https:" + url_part
                image_urls.append(url_part)

print("Product-Slider image URLs:")
for url in set(image_urls):
    print(url)

os.makedirs("downloaded_images", exist_ok=True)
for idx, img_url in enumerate(set(image_urls)):
    try:
        img_data = requests.get(img_url).content
        with open(f"downloaded_images/image_{idx+1}.jpg", "wb") as f:
            f.write(img_data)
        print(f"Downloaded: {img_url}")
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")