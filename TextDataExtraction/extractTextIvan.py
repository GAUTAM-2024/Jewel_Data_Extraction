"""
Ivan Jewels Product Data Extraction Script
Extracts product information from Ivan Jewels product pages
Supports single URL or batch processing via Excel file

Single URL Usage:
  python extractTextIvan.py -u "https://ivanajewels.com/products/..." --show-table

Excel File Usage:
  python extractTextIvan.py -f "input.xlsx" -o "output.xlsx"

Required Excel Columns:
- product_id: Product ID (optional for single URL)
- Source Link: Product URL
- Product Type: Necklace, Earrings, Rings, Bracelet (optional for single URL)

Output Fields:
- Product Id, Source URL, Product Name, Default Price, Description
- Metal Colors, Metal Carats, Categories, 14K Price, 18K Price
- Size Options (for Rings and Bracelet)
"""

import argparse
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
from tabulate import tabulate


def fetch_html_from_url(url, retries=3, delay=2):
    """
    Fetch HTML content from URL with retry logic
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    
    return None


def extract_product_data(html_content, source_url=None, product_id=None, product_type=None):
    """
    Extract product data from Ivan Jewels product page HTML
    
    Args:
        html_content: HTML string of the product page
        source_url: Original URL
        product_id: Product ID from Excel
        product_type: Product Type from Excel (Necklace, Earrings, Rings, Bracelet)
        
    Returns:
        Dictionary containing extracted product information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    product_data = {
        'product_id': product_id,
        'source_url': source_url,
        'product_name': None,
        'default_price': None,
        'description': None,
        'metal_colors': [],
        'metal_carats': [],
        'categories': [],
        'price_14k': None,
        'price_18k': None,
        'size_options': [],  # For Rings and Bracelet
        'product_type': product_type
    }
    
    # Extract Product Name
    product_title = soup.find('h1', class_='product-title')
    if product_title:
        product_data['product_name'] = product_title.get_text(strip=True)
    
    # Extract Default Price
    price_span = soup.find('ins')
    if price_span:
        amount = price_span.find('span', class_='amount')
        if amount:
            product_data['default_price'] = amount.get_text(strip=True)
    
    # Extract Description
    description_collapsible = soup.find('collapsible-row', class_='collapsible-description')
    if description_collapsible:
        desc_content = description_collapsible.find('div', class_='collapsible__content')
        if desc_content:
            product_data['description'] = desc_content.get_text(strip=True)
    
    # Extract Metal Color Options
    color_fieldset = soup.find('fieldset', {'data-handle': 'color'})
    if color_fieldset:
        color_inputs = color_fieldset.find_all('input', {'type': 'radio', 'name': 'Color'})
        for inp in color_inputs:
            color_value = inp.get('value')
            if color_value and color_value not in product_data['metal_colors']:
                product_data['metal_colors'].append(color_value)
    
    # Extract Metal Carat Options
    carat_fieldset = soup.find('fieldset', {'data-handle': 'carats'})
    if carat_fieldset:
        carat_inputs = carat_fieldset.find_all('input', {'type': 'radio', 'name': 'Carats'})
        for inp in carat_inputs:
            carat_value = inp.get('value')
            if carat_value and carat_value not in product_data['metal_carats']:
                product_data['metal_carats'].append(carat_value)
    
    # Extract Size Options (for Rings and Bracelet)
    # Method 1: Check for Ring Size select - name contains "Ring Size"
    ring_size_select = soup.find('select', {'name': lambda x: x and 'Ring Size' in x})
    if ring_size_select:
        size_options = ring_size_select.find_all('option')
        for opt in size_options:
            size_text = opt.get_text(strip=True)
            if size_text and size_text not in product_data['size_options']:
                product_data['size_options'].append(size_text)
    
    # Method 2: Check for Bracelet Size select - name contains "Bracelet" or "Braceletes"
    if not product_data['size_options']:
        bracelet_size_select = soup.find('select', {'name': lambda x: x and ('Bracelet' in x or 'Braceletes' in x)})
        if bracelet_size_select:
            size_options = bracelet_size_select.find_all('option')
            for opt in size_options:
                size_text = opt.get_text(strip=True)
                if size_text and size_text not in product_data['size_options']:
                    product_data['size_options'].append(size_text)
    
    # Method 3: Fallback - Check for fieldset with product-information--line-item class
    if not product_data['size_options']:
        line_item_fieldsets = soup.find_all('fieldset', class_='product-information--line-item')
        for fieldset in line_item_fieldsets:
            label_div = fieldset.find('div', class_='form__label')
            if label_div:
                label_text = label_div.get_text(strip=True).lower()
                if 'size' in label_text or 'ring' in label_text or 'bracelet' in label_text:
                    select_div = fieldset.find('div', class_='select')
                    if select_div:
                        select_elem = select_div.find('select')
                        if select_elem:
                            size_options = select_elem.find_all('option')
                            for opt in size_options:
                                size_text = opt.get_text(strip=True)
                                if size_text and size_text not in product_data['size_options']:
                                    product_data['size_options'].append(size_text)
                    break
    
    # Method 4: Check for size fieldset with data-handle='size'
    if not product_data['size_options']:
        size_fieldset = soup.find('fieldset', {'data-handle': 'size'})
        if size_fieldset:
            size_inputs = size_fieldset.find_all('input', {'type': 'radio'})
            for inp in size_inputs:
                size_value = inp.get('value')
                if size_value and size_value not in product_data['size_options']:
                    product_data['size_options'].append(size_value)
    
    # Extract Categories
    categories_div = soup.find('div', class_='categories-inline')
    if categories_div:
        category_links = categories_div.find_all('a')
        for link in category_links:
            cat_name = link.get_text(strip=True)
            if cat_name:
                product_data['categories'].append(cat_name)
    
    # Extract 14K and 18K Pricing from Variants JSON
    script_tags = soup.find_all('script', {'type': 'application/json'})
    for script in script_tags:
        try:
            json_data = json.loads(script.string)
            if isinstance(json_data, list) and len(json_data) > 0:
                if 'title' in json_data[0] and 'price' in json_data[0]:
                    # Extract pricing by carat (same price for all colors)
                    for variant in json_data:
                        carat = variant.get('option2')  # Carat is typically option2
                        price = variant.get('price')
                        if carat and price:
                            price_formatted = f"₹ {price / 100:,.0f}"
                            if '14' in str(carat) and not product_data['price_14k']:
                                product_data['price_14k'] = price_formatted
                            elif '18' in str(carat) and not product_data['price_18k']:
                                product_data['price_18k'] = price_formatted
        except (json.JSONDecodeError, TypeError):
            continue
    
    return product_data


def display_as_table(product_data):
    """Display extracted data in table format"""
    
    print("\n" + "="*80)
    print("IVAN JEWELS - PRODUCT DATA EXTRACTION")
    print("="*80)
    
    # Basic Product Info Table
    basic_info = [
        ["Product ID", product_data.get('product_id', 'N/A')],
        ["Source URL", product_data.get('source_url', 'N/A')],
        ["Product Name", product_data.get('product_name')],
        ["Product Type", product_data.get('product_type', 'N/A')],
        ["Default Price", product_data.get('default_price')],
        ["14K Price", product_data.get('price_14k', 'N/A')],
        ["18K Price", product_data.get('price_18k', 'N/A')],
        ["Metal Colors", ', '.join(product_data.get('metal_colors', []))],
        ["Metal Carats", ', '.join(product_data.get('metal_carats', []))],
        ["Categories", ', '.join(product_data.get('categories', []))]
    ]
    
    # Add Size Options if available
    if product_data.get('size_options'):
        basic_info.append(["Size Options", ', '.join(product_data.get('size_options', []))])
    
    print("\n📦 PRODUCT INFORMATION")
    print(tabulate(basic_info, headers=["Field", "Value"], tablefmt="grid"))
    
    # Description
    if product_data.get('description'):
        print("\n📝 DESCRIPTION")
        print("-" * 80)
        print(product_data['description'])
        print("-" * 80)
    
    print("\n" + "="*80)
    if diamond_table:
        table = diamond_table.find('table')
        if table:
            rows = table.find_all('tr')
            headers = []
            for row in rows:
                ths = row.find_all('th')
                if ths:
                    headers = [th.get_text(strip=True) for th in ths]
                else:
                    tds = row.find_all('td')
                    if tds and headers:
                        stone_data = {}
                        for i, td in enumerate(tds):
                            if i < len(headers):
                                stone_data[headers[i]] = td.get_text(strip=True)
                        if stone_data:
                            product_data['diamond_gemstones'].append(stone_data)
    
    # Extract Price Breakup
    price_breakup_div = soup.find('div', id=lambda x: x and 'price-breakdown' in str(x))
    if price_breakup_div:
        table = price_breakup_div.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 2:
                    item_name = tds[0].get_text(strip=True)
                    item_price = tds[1].get_text(strip=True)
                    product_data['price_breakup'].append({
                        'item': item_name,
                        'price': item_price
                    })
    
    # Extract Gold Weight, Product Weight, and Purity from Specification
    spec_collapsible = soup.find('collapsible-row', class_='collapsible-specification')
    if spec_collapsible:
        # Gold Purity and Weight
        purity_div = spec_collapsible.find('div', id='varient-description-purity')
        if purity_div:
            paragraphs = purity_div.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                classes = p.get('class', [])
                if 'total-weight' in classes:
                    product_data['gold_weight'] = text
                elif 'Gold' in text:
                    product_data['gold_purity'] = text
        
        # Product Weight
        weight_div = spec_collapsible.find('div', id='varient-description-weight')
        if weight_div:
            weight_p = weight_div.find('p', class_='total-weight')
            if weight_p:
                product_data['product_weight'] = weight_p.get_text(strip=True)
    
    # Extract Important Guide
    important_collapsible = soup.find('collapsible-row', class_='collapsible-important-guide')
    if important_collapsible:
        guide_content = important_collapsible.find('div', class_='collapsible__content')
        if guide_content:
            product_data['important_guide'] = guide_content.get_text(strip=True)
    
    return product_data


def display_as_table(product_data):
    """Display extracted data in table format"""
    
    print("\n" + "="*80)
    print("IVAN JEWELS - PRODUCT DATA EXTRACTION")
    print("="*80)
    
    # Basic Product Info Table
    basic_info = [
        ["Product Name", product_data['product_name']],
        ["Product Type", product_data.get('product_type', 'N/A')],
        ["SKU", product_data['sku']],
        ["Price", product_data['price']],
        ["Gold Purity", product_data['gold_purity']],
        ["Gold Weight", product_data['gold_weight']],
        ["Product Weight", product_data['product_weight']],
        ["Source URL", product_data.get('source_url', 'N/A')]
    ]
    print("\n📦 BASIC PRODUCT INFORMATION")
    print(tabulate(basic_info, headers=["Field", "Value"], tablefmt="grid"))
    
    # Description
    if product_data['description']:
        print("\n📝 DESCRIPTION")
        print("-" * 80)
        print(product_data['description'])
        print("-" * 80)
    
    # Metal Color Options Table
    if product_data['metal_color_options']:
        print("\n🎨 METAL COLOR OPTIONS")
        color_table = [[opt['color'], "✓" if opt['selected'] else "", opt['availability']] 
                       for opt in product_data['metal_color_options']]
        print(tabulate(color_table, headers=["Color", "Selected", "Availability"], tablefmt="grid"))
    
    # Metal Carat Options Table with Pricing
    if product_data['carat_pricing']:
        print("\n💎 METAL CARAT OPTIONS & PRICING")
        carat_table = [[cp['carat'], cp['price_formatted']] 
                       for cp in product_data['carat_pricing']]
        print(tabulate(carat_table, headers=["Carat", "Price"], tablefmt="grid"))
    elif product_data['metal_carat_options']:
        print("\n💎 METAL CARAT OPTIONS")
        carat_table = [[opt['carat'], "✓" if opt['selected'] else "", opt['availability']] 
                       for opt in product_data['metal_carat_options']]
        print(tabulate(carat_table, headers=["Carat", "Selected", "Availability"], tablefmt="grid"))
    
    # Size Options Table (for rings and bracelets)
    if product_data['size_options']:
        print("\n📏 SIZE OPTIONS")
        size_table = [[opt['size'], "✓" if opt['selected'] else ""] 
                      for opt in product_data['size_options']]
        print(tabulate(size_table, headers=["Size", "Selected"], tablefmt="grid"))
    
    # Variants Table (with pricing) - Show only if needed for detailed view
    if product_data['variants'] and len(product_data['variants']) > 0:
        print("\n💰 ALL VARIANTS (Detailed)")
        variant_table = [[v['title'], v['sku'], f"₹ {v['price']:,.2f}" if v['price'] else "N/A", 
                         "Yes" if v['available'] else "No"] 
                        for v in product_data['variants']]
        print(tabulate(variant_table, headers=["Variant", "SKU", "Price", "Available"], tablefmt="grid"))
    
    # Diamond & Gemstones Table
    if product_data['diamond_gemstones']:
        print("\n💠 DIAMOND & GEMSTONES")
        headers = list(product_data['diamond_gemstones'][0].keys())
        gem_table = [[stone.get(h, '') for h in headers] for stone in product_data['diamond_gemstones']]
        print(tabulate(gem_table, headers=headers, tablefmt="grid"))
    
    # Price Breakup Table
    if product_data['price_breakup']:
        print("\n💵 PRICE BREAKUP")
        price_table = [[item['item'], item['price']] for item in product_data['price_breakup']]
        print(tabulate(price_table, headers=["Component", "Price"], tablefmt="grid"))
    
    # Categories Table
    if product_data['categories']:
        print("\n🏷️ CATEGORIES")
        cat_table = [[cat] for cat in product_data['categories']]
        print(tabulate(cat_table, headers=["Category"], tablefmt="grid"))
    
    print("\n" + "="*80)


def flatten_product_data(product_data):
    """
    Flatten product data for Excel export (single row per product)
    
    Returns:
        Dictionary with flattened data suitable for DataFrame
    """
    flat_data = {
        'Product Id': product_data.get('product_id'),
        'Source URL': product_data.get('source_url'),
        'Product Name': product_data.get('product_name'),
        'Product Type': product_data.get('product_type'),
        'Default Price': product_data.get('default_price'),
        'Description': product_data.get('description'),
        'Metal Colors': ', '.join(product_data.get('metal_colors', [])),
        'Metal Carats': ', '.join(product_data.get('metal_carats', [])),
        'Categories': ', '.join(product_data.get('categories', [])),
        '14K Price': product_data.get('price_14k'),
        '18K Price': product_data.get('price_18k'),
    }
    
    # Add Size Options for Rings and Bracelet
    if product_data.get('size_options'):
        flat_data['Size Options'] = ', '.join(product_data.get('size_options', []))
    
    return flat_data


def create_output_dataframe(all_products_data):
    """
    Create DataFrame from extracted product data for Excel export
    
    Returns:
        DataFrame with all products
    """
    products_list = []
    
    for product in all_products_data:
        products_list.append(flatten_product_data(product))
    
    output_df = pd.DataFrame(products_list)
    
    # Reorder columns as per requirement
    column_order = [
        'Product Id', 'Source URL', 'Product Name', 'Product Type',
        'Default Price', 'Description', 'Metal Colors', 'Metal Carats',
        'Categories', '14K Price', '18K Price'
    ]
    
    # Add Size Options if present
    if 'Size Options' in output_df.columns:
        column_order.append('Size Options')
    
    # Filter to only existing columns
    column_order = [col for col in column_order if col in output_df.columns]
    output_df = output_df[column_order]
    
    return output_df


def process_ivan_url(url, product_id=None, product_type=None):
    """
    Process a single Ivan Jewels URL
    
    Args:
        url: Product page URL
        product_id: Product ID from Excel
        product_type: Product Type from Excel
        
    Returns:
        Extracted product data dictionary or None if failed
    """
    print(f"  Fetching HTML from URL...")
    html_content = fetch_html_from_url(url)
    
    if not html_content:
        print(f"  ❌ Failed to fetch HTML")
        return None
    
    print(f"  Extracting product data...")
    product_data = extract_product_data(
        html_content, 
        source_url=url,
        product_id=product_id,
        product_type=product_type
    )
    
    if product_data.get('product_name'):
        print(f"  ✅ Extracted: {product_data['product_name']}")
        return product_data
    else:
        print(f"  ⚠️ No product data found")
        return None


def main():
    parser = argparse.ArgumentParser(description="Extract Product Data from Ivan Jewels Website")

    # Mutually exclusive group for URL or File
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--url", help="Single Product URL to fetch")
    group.add_argument("-f", "--file", help="Path of Excel file containing URLs")
    
    parser.add_argument("-o", "--output", help="Output Excel file path (optional)")
    parser.add_argument("--show-table", action="store_true", help="Display results in table format")

    args = parser.parse_args()

    all_products_data = []

    # Single URL Processing
    if args.url:
        print(f"\n🔗 Processing Single URL: {args.url}")
        
        try:
            product_data = process_ivan_url(
                args.url, 
                product_id=None, 
                product_type=None
            )
            if product_data:
                all_products_data.append(product_data)
                # Always show table for single URL
                display_as_table(product_data)
        except Exception as e:
            print(f"  ❌ Error processing: {e}")
    
    # Excel File Processing
    elif args.file:
        print(f"\n📂 Processing File: {args.file}")
        
        # Read Excel File
        try:
            df = pd.read_excel(args.file)
        except Exception as e:
            print(f"❌ Error reading Excel file: {e}")
            return
        
        # Check for Source Link column (required)
        if 'Source Link' not in df.columns:
            print(f"❌ Excel file must have 'Source Link' column")
            return
        
        # Optional columns - use None if not present
        has_product_id = 'product_id' in df.columns
        has_product_type = 'Product Type' in df.columns
        
        if not has_product_id:
            print(f"   ⚠️ 'product_id' column not found - will be set to None")
        if not has_product_type:
            print(f"   ⚠️ 'Product Type' column not found - will be set to None")
        
        total_urls = len(df)
        print(f"   Found {total_urls} products to process\n")
        
        for idx, row in df.iterrows():
            url = row['Source Link']
            product_id = row.get('product_id') if has_product_id else None
            product_type = row.get('Product Type') if has_product_type else None
            
            print(f"\n[{idx + 1}/{total_urls}] Processing: {url}")
            if product_id or product_type:
                print(f"   Product ID: {product_id} | Type: {product_type}")
            
            try:
                product_data = process_ivan_url(
                    url, 
                    product_id=product_id, 
                    product_type=product_type
                )
                if product_data:
                    all_products_data.append(product_data)
                    if args.show_table:
                        display_as_table(product_data)
            except Exception as e:
                print(f"  ❌ Error processing: {e}")
            
            # Add delay to avoid rate limiting
            if idx < total_urls - 1:
                time.sleep(1)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 EXTRACTION SUMMARY")
    print(f"{'='*80}")
    print(f"   Total Products Processed: {len(all_products_data)}")
    
    # Export to Excel
    if all_products_data:
        output_df = create_output_dataframe(all_products_data)
        
        # Determine output path
        if args.output:
            output_path = args.output
        elif args.file:
            output_path = args.file.replace('.xlsx', '_extracted.xlsx').replace('.xls', '_extracted.xlsx')
        else:
            output_path = 'ivan_extracted.xlsx'
        
        try:
            output_df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"\n✅ Data exported to: {output_path}")
            print(f"   Total rows: {len(output_df)}")
        except Exception as e:
            print(f"❌ Error exporting to Excel: {e}")
    else:
        print(f"\n⚠️ No data to export")
    
    print(f"\n{'='*80}")
    
    return all_products_data


if __name__ == "__main__":
    main()
