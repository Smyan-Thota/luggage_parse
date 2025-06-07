"""
Rimowa luggage scraper - WITH MONGODB INTEGRATION
• Collects ONLY /luggage/ product pages
• Reads canonical specs from JSON-LD (price, sku, color, size, weight, dims…)
• Clicks "SIZE & WEIGHT" accordion as a fallback for dimensions
• Outputs two CSVs: all_rows.csv (incl. duplicates) and unique_by_sku.csv
• Automatically uploads data to MongoDB
"""

import csv, json, re, time, sys
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

# ── MongoDB Configuration ────────────────────────────────────────
MONGODB_CONNECTION = "<insert string here>"
DB_NAME = "rimowa_luggage"
COLLECTION_UNIQUE = "rimowa"
COLLECTION_ALL = "rimowa_all"

# ── Selenium setup ───────────────────────────────────────────────
opt = Options()
opt.add_argument("--headless=new")
opt.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=opt)
wait   = WebDriverWait(driver, 10)

# ── helpers ──────────────────────────────────────────────────────
def jsonld_product(soup: BeautifulSoup) -> dict:
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string)
            if isinstance(data, list):
                for d in data:
                    if d.get("@type") == "Product":
                        return d
            elif data.get("@type") == "Product":
                return data
        except Exception:
            pass
    return {}

def open_size_weight():
    """Click accordion so specs are visible (needed on a few pages)."""
    try:
        # Try multiple selectors for the size/weight accordion
        selectors = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'size')]",
            "//button[contains(@class,'accordion') and contains(.,'SIZE')]",
            "//div[@class='accordion-title' and contains(.,'SIZE')]",
            "//button[contains(.,'SIZE & WEIGHT')]"
        ]
        
        for selector in selectors:
            try:
                btn = driver.find_element(By.XPATH, selector)
                if btn and btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                    break
            except:
                continue
    except Exception:
        pass

def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()

def extract_dimensions_weight(soup: BeautifulSoup):
    """Extract dimensions and weight from various page elements."""
    dims_cm = dims_in = w_kg = w_lb = ""
    
    # Look for specification lists
    spec_containers = soup.find_all(['ul', 'div'], class_=re.compile(r'spec|detail|feature|attribute', re.I))
    
    for container in spec_containers:
        text = container.get_text(" ", strip=True)
        
        # Look for dimensions
        if not dims_cm or not dims_in:
            # Pattern 1: "Dimensions: XX x YY x ZZ cm (AA x BB x CC inch)"
            dim_match = re.search(r'(?:dimension|measurement|size)[:\s]*([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*cm[^(]*\(([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*inch', text, re.I)
            if dim_match:
                dims_cm = f"{dim_match.group(1)} cm"
                dims_in = f"{dim_match.group(2)} inch"
            else:
                # Pattern 2: Separate cm and inch mentions
                cm_match = re.search(r'([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*cm', text, re.I)
                in_match = re.search(r'([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*(?:inch|in|")', text, re.I)
                if cm_match:
                    dims_cm = f"{cm_match.group(1)} cm"
                if in_match:
                    dims_in = f"{in_match.group(1)} inch"
        
        # Look for weight
        if not w_kg or not w_lb:
            # Pattern 1: "Weight: XX kg (YY lbs)"
            weight_match = re.search(r'weight[:\s]*([\d.,]+)\s*kg[^(]*\(([\d.,]+)\s*(?:lb|lbs)', text, re.I)
            if weight_match:
                w_kg = f"{weight_match.group(1)} kg"
                w_lb = f"{weight_match.group(2)} lbs"
            else:
                # Pattern 2: Separate kg and lbs mentions
                kg_match = re.search(r'weight[:\s]*([\d.,]+)\s*kg', text, re.I)
                lb_match = re.search(r'weight[:\s]*([\d.,]+)\s*(?:lb|lbs)', text, re.I)
                if kg_match:
                    w_kg = f"{kg_match.group(1)} kg"
                if lb_match:
                    w_lb = f"{lb_match.group(1)} lbs"
    
    # Also check list items specifically
    for li in soup.find_all('li'):
        text = clean(li.get_text(" ", strip=True))
        
        if not dims_cm or not dims_in:
            if 'measurement' in text.lower() or 'dimension' in text.lower():
                # Try to extract dimensions
                cm_match = re.search(r'([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*cm', text, re.I)
                in_match = re.search(r'([\d.,]+\s*x\s*[\d.,]+\s*x\s*[\d.,]+)\s*(?:inch|in|")', text, re.I)
                if cm_match and not dims_cm:
                    dims_cm = f"{cm_match.group(1)} cm"
                if in_match and not dims_in:
                    dims_in = f"{in_match.group(1)} inch"
        
        if not w_kg or not w_lb:
            if 'weight' in text.lower():
                kg_match = re.search(r'([\d.,]+)\s*kg', text, re.I)
                lb_match = re.search(r'([\d.,]+)\s*(?:lb|lbs)', text, re.I)
                if kg_match and not w_kg:
                    w_kg = f"{kg_match.group(1)} kg"
                if lb_match and not w_lb:
                    w_lb = f"{lb_match.group(1)} lbs"
    
    return dims_cm, dims_in, w_kg, w_lb

def upload_to_mongodb(csv_filepath, collection_name):
    """Upload CSV data to MongoDB collection."""
    try:
        print(f"\n📤 Uploading {csv_filepath} to MongoDB collection '{collection_name}'...")
        
        # Connect to MongoDB
        client = MongoClient(MONGODB_CONNECTION, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✓ Connected to MongoDB")
        
        db = client[DB_NAME]
        collection = db[collection_name]
        
        # Read CSV with pandas
        df = pd.read_csv(csv_filepath)
        df = df.where(pd.notnull(df), None)
        products = df.to_dict('records')
        
        inserted_count = 0
        updated_count = 0
        
        for product in products:
            # Clean up the product data
            clean_product = {}
            for key, value in product.items():
                if value == "" or (isinstance(value, str) and value.strip() == ""):
                    clean_product[key] = None
                else:
                    clean_product[key] = value
            
            # Add metadata
            clean_product['last_updated'] = datetime.now()
            clean_product['source'] = 'rimowa_scraper'
            
            # Parse price to float
            if clean_product.get('Price'):
                try:
                    price_str = clean_product['Price'].replace('$', '').replace(',', '')
                    clean_product['price_numeric'] = float(price_str)
                except:
                    pass
            
            # Upsert based on SKU or Product URL
            identifier_field = 'SKU' if clean_product.get('SKU') else 'Product URL'
            identifier_value = clean_product.get(identifier_field)
            
            if identifier_value:
                result = collection.update_one(
                    {identifier_field: identifier_value},
                    {'$set': clean_product},
                    upsert=True
                )
                
                if result.upserted_id:
                    inserted_count += 1
                else:
                    updated_count += 1
        
        # Create indexes
        collection.create_index("SKU")
        collection.create_index("Product URL")
        collection.create_index("price_numeric")
        
        print(f"✓ Upload complete: {inserted_count} new, {updated_count} updated")
        print(f"  Total documents in collection: {collection.count_documents({})}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ MongoDB upload failed: {e}")
        return False

# ── collect product URLs ─────────────────────────────────────────
print("🔍 Starting Rimowa product scraper...")
print("="*60)

categories = {
    "Cabin"      : "https://www.rimowa.com/us/en/cabin-size/",
    "Check-In"   : "https://www.rimowa.com/us/en/check-in-size/",
    "Trunk"      : "https://www.rimowa.com/us/en/large-luggage/",
    "All"        : "https://www.rimowa.com/us/en/all-luggage/",
}

urls_all = []

for cat, url in categories.items():
    print(f"\n📂 Collecting links from {cat} category...")
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # load all items if "More Results" exists
    while True:
        try:
            btn = driver.find_element(By.LINK_TEXT, "More Results")
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            time.sleep(1)
        except Exception:
            break

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cat_count = 0
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.startswith("/"): h = "https://www.rimowa.com"+h
        if not h.endswith(".html"):              # need product page
            continue
        if not re.search(r"/us/en/luggage/", h): # ignore stickers, bags, stories…
            continue
        urls_all.append((h, cat))
        cat_count += 1
    
    print(f"  Found {cat_count} products")

print(f"\n📊 Total links collected: {len(urls_all)}")
print("="*60)

# ── scrape each product page ─────────────────────────────────────
print("\n🕷️ Scraping product pages...")
rows = []
seen = set()

for idx, (url, cat) in enumerate(urls_all, 1):
    print(f"\n[{idx}/{len(urls_all)}] Scraping: {url}")
    
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)  # Give page time to fully load
    except Exception as e:
        print(f"  ✗ Load failed: {e}")
        continue

    # Try to open size/weight accordion
    open_size_weight()
    
    # Wait a bit more after clicking accordion
    time.sleep(0.5)
    
    soup  = BeautifulSoup(driver.page_source, "html.parser")
    pdata = jsonld_product(soup)
    if not pdata:
        print(f"  ✗ No JSON-LD data found")
        continue

    sku   = str(pdata.get("sku", "")).strip()
    name  = clean(pdata.get("name", ""))
    image = pdata["image"][0] if isinstance(pdata.get("image"), list) else pdata.get("image","")

    # colors – JSON-LD may give a list or string
    colors = pdata.get("color", [])
    if isinstance(colors, str): colors = [colors]
    colors = ", ".join(dict.fromkeys([clean(c) for c in colors]))

    # material – from description or Outside spec
    material = ""
    m = re.search(r"Outside\s*:\s*([A-Za-z ]+)", soup.get_text(" ", strip=True))
    if m: material = clean(m.group(1))
    if not material:
        txt = (name + soup.get_text(" ", strip=True)).lower()
        for key in ("Aluminum","Aluminium","Polycarbonate","Leather"):
            if key.lower() in txt: material = key; break

    # dimension / weight – first try JSON-LD quantitative values
    dims_cm = dims_in = w_kg = w_lb = ""
    
    # Check if dimensions are in additionalProperty first
    if pdata.get("additionalProperty"):
        for prop in pdata["additionalProperty"]:
            prop_name = prop.get("name", "").lower()
            prop_value = clean(prop.get("value", ""))
            
            if prop_name == "dimensions" and prop_value:
                # Parse the dimension string
                if "cm" in prop_value and "inch" in prop_value:
                    # Format: "XX x YY x ZZ cm (AA x BB x CC inch)"
                    parts = prop_value.split("(")
                    if len(parts) == 2:
                        dims_cm = parts[0].strip()
                        dims_in = parts[1].replace(")", "").strip()
                elif "inch" in prop_value:
                    dims_in = prop_value
                elif "cm" in prop_value:
                    dims_cm = prop_value
            
            elif prop_name == "weight" and prop_value:
                # Parse the weight string
                if "kg" in prop_value and "lb" in prop_value:
                    # Format: "XX kg (YY lbs)"
                    parts = prop_value.split("(")
                    if len(parts) == 2:
                        w_kg = parts[0].strip()
                        w_lb = parts[1].replace(")", "").strip()
                elif "kg" in prop_value:
                    w_kg = prop_value
                elif "lb" in prop_value:
                    w_lb = prop_value
    
    # Try depth/height/width from JSON-LD
    if not dims_cm:
        depth = pdata.get("depth", {})
        height = pdata.get("height", {})
        width = pdata.get("width", {})
        
        # Extract values if they're objects with value/unitText
        if isinstance(depth, dict): depth = depth.get("value", "")
        if isinstance(height, dict): height = height.get("value", "")
        if isinstance(width, dict): width = width.get("value", "")
        
        if depth and height and width:
            dims_cm = f"{width} x {height} x {depth} cm"
    
    # Try weight from JSON-LD
    if not w_kg:
        wqv = pdata.get("weight", {})
        if isinstance(wqv, dict) and wqv.get("value"):
            unit = wqv.get("unitText", "kg").lower()
            value = wqv.get("value")
            if "kg" in unit:
                w_kg = f"{value} kg"
            elif "lb" in unit:
                w_lb = f"{value} lbs"
    
    # Fallback: extract from page text
    if not dims_cm or not dims_in or not w_kg or not w_lb:
        extracted = extract_dimensions_weight(soup)
        if not dims_cm: dims_cm = extracted[0]
        if not dims_in: dims_in = extracted[1]
        if not w_kg: w_kg = extracted[2]
        if not w_lb: w_lb = extracted[3]

    # variant & price – walk JSON-LD offers
    offers = pdata.get("offers", [])
    if isinstance(offers, dict): offers=[offers]
    
    product_count = 0
    for off in offers:
        try:
            price = float(off.get("price", 0))
        except (KeyError, ValueError, TypeError): 
            continue
        if price < 100:                       # ignore sticker addons etc.
            continue
        price_str = f"${price:,.2f}"

        size_variant = off.get("variant") or off.get("name") or ""
        # use offer SKU if present (often the same as top SKU)
        offer_sku = off.get("sku") or sku
        key = offer_sku or (url+size_variant)  # for dedup unique table

        row = {
            "Product URL"     : url,
            "Product Name"    : name,
            "Variant Size"    : clean(size_variant),
            "Price"           : price_str,
            "Dimensions (cm)" : dims_cm,
            "Dimensions (in)" : dims_in,
            "Weight (kg)"     : w_kg,
            "Weight (lbs)"    : w_lb,
            "Colors"          : colors,
            "Material"        : material,
            "SKU"             : offer_sku,
            "Category"        : "Luggage",
            "Subcategory"     : cat,
            "Main Image URL"  : image,
        }
        rows.append(row)
        product_count += 1
        if key not in seen:
            seen.add(key)

    print(f"  ✓ Extracted {product_count} variants - Dims: {dims_cm or 'None'}, Weight: {w_kg or 'None'}")

print(f"\n📊 Scraping complete! Total product variants: {len(rows)}")
print("="*60)

# ── write CSVs ────────────────────────────────────────────────────
print("\n💾 Writing CSV files...")
headers = ["Product URL","Product Name","Variant Size","Price",
           "Dimensions (cm)","Dimensions (in)","Weight (kg)","Weight (lbs)",
           "Colors","Material","SKU","Category","Subcategory","Main Image URL"]

# all rows
all_csv = "rimowa_all_products.csv"
with Path(all_csv).open("w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, headers)
    w.writeheader(); w.writerows(rows)
print(f"✓ Created: {all_csv}")

# unique rows (by SKU+variant key stored in 'seen')
unique_csv = "rimowa_unique_products.csv"
unique = { (r["SKU"] or r["Product URL"]+r["Variant Size"]): r for r in rows }.values()
with Path(unique_csv).open("w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, headers)
    w.writeheader(); w.writerows(unique)
print(f"✓ Created: {unique_csv}")

# ── Upload to MongoDB ─────────────────────────────────────────────
print("\n🔄 Starting MongoDB upload...")
print("="*60)

# Test MongoDB connection first
try:
    test_client = MongoClient(MONGODB_CONNECTION, serverSelectionTimeoutMS=5000)
    test_client.admin.command('ping')
    test_client.close()
    print("✓ MongoDB connection verified")
    
    # Upload unique products
    upload_to_mongodb(unique_csv, COLLECTION_UNIQUE)
    
    # Upload all products (including duplicates)
    upload_to_mongodb(all_csv, COLLECTION_ALL)
    
    print("\n✅ All operations completed successfully!")
    
except Exception as e:
    print(f"\n⚠️ MongoDB upload skipped due to connection error: {e}")
    print("📌 CSV files have been saved locally.")
    print("\nTo upload later, ensure:")
    print("1. Your IP is whitelisted in MongoDB Atlas")
    print("2. Your credentials are correct")
    print("3. You have internet connectivity")

# Clean up
driver.quit()
print("\n🏁 Script finished!")
