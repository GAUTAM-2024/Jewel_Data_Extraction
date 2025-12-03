"""
Ivan Jewels Product Data Extraction Script
Extracts product information from Ivan Jewels product page HTML
"""

from bs4 import BeautifulSoup
import json
import re
import pandas as pd
from tabulate import tabulate


def extract_product_data(html_content):
    """
    Extract product data from Ivan Jewels product page HTML
    
    Args:
        html_content: HTML string of the product page
        
    Returns:
        Dictionary containing extracted product information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    product_data = {
        'product_name': None,
        'price': None,
        'sku': None,
        'description': None,
        'metal_color_options': [],
        'metal_carat_options': [],
        'categories': [],
        'variants': [],
        'diamond_gemstones': [],
        'price_breakup': [],
        'gold_weight': None,
        'product_weight': None,
        'important_guide': None
    }
    
    # Extract Product Name
    product_title = soup.find('h1', class_='product-title')
    if product_title:
        product_data['product_name'] = product_title.get_text(strip=True)
    
    # Extract Price
    price_span = soup.find('ins')
    if price_span:
        amount = price_span.find('span', class_='amount')
        if amount:
            product_data['price'] = amount.get_text(strip=True)
    
    # Extract SKU
    sku_div = soup.find('div', class_='product-variant-sku')
    if sku_div:
        sku_text = sku_div.get_text(strip=True)
        product_data['sku'] = sku_text.replace('SKU :', '').replace('SKU:', '').strip()
    
    # Extract Description
    description_details = soup.find('details', id=lambda x: x and 'collapsible_tab_6n6Kk3' in str(x))
    if description_details:
        desc_content = description_details.find('div', class_='collapsible__content')
        if desc_content:
            product_data['description'] = desc_content.get_text(strip=True)
    
    # Extract Metal Color Options
    color_fieldset = soup.find('fieldset', {'data-handle': 'color'})
    if color_fieldset:
        color_inputs = color_fieldset.find_all('input', {'type': 'radio', 'name': 'Color'})
        for inp in color_inputs:
            color_value = inp.get('value')
            is_checked = inp.has_attr('checked')
            variant_div = inp.find_parent('div', class_='custom-new-layout')
            availability = 'Made to order'
            if variant_div:
                qty_span = variant_div.find('span', class_='product-variant-qty')
                if qty_span:
                    availability = qty_span.get_text(strip=True)
            
            product_data['metal_color_options'].append({
                'color': color_value,
                'selected': is_checked,
                'availability': availability
            })
    
    # Extract Metal Carat Options
    carat_fieldset = soup.find('fieldset', {'data-handle': 'carats'})
    if carat_fieldset:
        carat_inputs = carat_fieldset.find_all('input', {'type': 'radio', 'name': 'Carats'})
        for inp in carat_inputs:
            carat_value = inp.get('value')
            is_checked = inp.has_attr('checked')
            variant_div = inp.find_parent('div', class_='custom-new-layout-alters')
            availability = 'Made to order'
            if variant_div:
                label = variant_div.find('label')
                if label:
                    qty_span = label.find('span', class_='product-variant-qty')
                    if qty_span:
                        availability = qty_span.get_text(strip=True)
            
            product_data['metal_carat_options'].append({
                'carat': carat_value,
                'selected': is_checked,
                'availability': availability
            })
    
    # Extract Categories
    categories_div = soup.find('div', class_='categories-inline')
    if categories_div:
        category_links = categories_div.find_all('a')
        for link in category_links:
            product_data['categories'].append({
                'name': link.get_text(strip=True),
                'url': link.get('href')
            })
    
    # Extract Variants from JSON
    script_tags = soup.find_all('script', {'type': 'application/json'})
    for script in script_tags:
        try:
            json_data = json.loads(script.string)
            if isinstance(json_data, list) and len(json_data) > 0:
                if 'title' in json_data[0] and 'price' in json_data[0]:
                    for variant in json_data:
                        product_data['variants'].append({
                            'id': variant.get('id'),
                            'title': variant.get('title'),
                            'sku': variant.get('sku'),
                            'option1': variant.get('option1'),  # Color
                            'option2': variant.get('option2'),  # Carat
                            'price': variant.get('price') / 100 if variant.get('price') else None,  # Convert from paise to rupees
                            'available': variant.get('available'),
                            'image_url': variant.get('featured_image', {}).get('src') if variant.get('featured_image') else None
                        })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Extract Diamond & Gemstones
    diamond_table = soup.find('div', id='varient-description-stone')
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
    
    # Extract Gold Weight and Product Weight
    spec_div = soup.find('div', class_='varient-description catalog-product-view')
    if spec_div:
        purity_div = spec_div.find('div', id='varient-description-purity')
        if purity_div:
            paragraphs = purity_div.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if 'g' in text and any(char.isdigit() for char in text):
                    if 'total-weight' in p.get('class', []):
                        product_data['gold_weight'] = text
        
        weight_div = spec_div.find('div', id='varient-description-weight')
        if weight_div:
            weight_p = weight_div.find('p', class_='total-weight')
            if weight_p:
                product_data['product_weight'] = weight_p.get_text(strip=True)
    
    # Extract Important Guide
    important_guide_details = soup.find('details', id=lambda x: x and 'collapsible_tab_ixwAe3' in str(x))
    if important_guide_details:
        guide_content = important_guide_details.find('div', class_='collapsible__content')
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
        ["SKU", product_data['sku']],
        ["Price", product_data['price']],
        ["Gold Weight", product_data['gold_weight']],
        ["Product Weight", product_data['product_weight']]
    ]
    print("\n📦 BASIC PRODUCT INFORMATION")
    print(tabulate(basic_info, headers=["Field", "Value"], tablefmt="grid"))
    
    # Description
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
    
    # Metal Carat Options Table
    if product_data['metal_carat_options']:
        print("\n💎 METAL CARAT OPTIONS")
        carat_table = [[opt['carat'], "✓" if opt['selected'] else "", opt['availability']] 
                       for opt in product_data['metal_carat_options']]
        print(tabulate(carat_table, headers=["Carat", "Selected", "Availability"], tablefmt="grid"))
    
    # Variants Table (with pricing)
    if product_data['variants']:
        print("\n💰 VARIANT PRICING")
        variant_table = [[v['title'], v['sku'], f"₹ {v['price']:,.2f}" if v['price'] else "N/A", 
                         "Yes" if v['available'] else "No"] 
                        for v in product_data['variants']]
        print(tabulate(variant_table, headers=["Variant", "SKU", "Price", "Available"], tablefmt="grid"))
    
    # Diamond & Gemstones Table
    if product_data['diamond_gemstones']:
        print("\n💠 DIAMOND & GEMSTONES")
        if product_data['diamond_gemstones']:
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
        cat_table = [[cat['name']] for cat in product_data['categories']]
        print(tabulate(cat_table, headers=["Category"], tablefmt="grid"))
    
    print("\n" + "="*80)


def export_to_dataframes(product_data):
    """Export extracted data to pandas DataFrames"""
    
    # Basic Info DataFrame
    basic_df = pd.DataFrame([{
        'Product Name': product_data['product_name'],
        'SKU': product_data['sku'],
        'Price': product_data['price'],
        'Gold Weight': product_data['gold_weight'],
        'Product Weight': product_data['product_weight'],
        'Description': product_data['description']
    }])
    
    # Variants DataFrame
    variants_df = pd.DataFrame(product_data['variants'])
    
    # Color Options DataFrame
    colors_df = pd.DataFrame(product_data['metal_color_options'])
    
    # Carat Options DataFrame
    carats_df = pd.DataFrame(product_data['metal_carat_options'])
    
    # Diamond & Gemstones DataFrame
    diamonds_df = pd.DataFrame(product_data['diamond_gemstones'])
    
    # Price Breakup DataFrame
    price_df = pd.DataFrame(product_data['price_breakup'])
    
    # Categories DataFrame
    categories_df = pd.DataFrame(product_data['categories'])
    
    return {
        'basic_info': basic_df,
        'variants': variants_df,
        'color_options': colors_df,
        'carat_options': carats_df,
        'diamonds': diamonds_df,
        'price_breakup': price_df,
        'categories': categories_df
    }


def main():
    """Main function to demonstrate extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract Product Data from Ivan Jewels HTML")
    parser.add_argument("-f", "--file", required=True, help="Path to HTML file")
    parser.add_argument("-o", "--output", help="Output Excel file path (optional)")
    
    args = parser.parse_args()
    
    # Read HTML file
    with open(args.file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract data
    product_data = extract_product_data(html_content)
    
    # Display as table
    display_as_table(product_data)
    
    # Export to Excel if output path provided
    if args.output:
        dfs = export_to_dataframes(product_data)
        with pd.ExcelWriter(args.output, engine='openpyxl') as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"\n✅ Data exported to: {args.output}")
    
    return product_data


if __name__ == "__main__":
    main()
