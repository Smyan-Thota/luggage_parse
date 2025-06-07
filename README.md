# Rimowa Luggage Scraper

A comprehensive web scraper for extracting product information from Rimowa's official website. This tool automatically collects product details including specifications, pricing, and images, then saves the data to both CSV files and MongoDB.

## 🎯 Features

- **Multi-Category Scraping**: Automatically scrapes Cabin, Check-In, Trunk, and All luggage categories
- **Comprehensive Data Extraction**: Collects product names, SKUs, prices, dimensions, weights, colors, materials, and images
- **JSON-LD Parsing**: Reads structured product data directly from website markup
- **Fallback Extraction**: Uses multiple methods to ensure data completeness
- **Duplicate Handling**: Creates both complete and unique product datasets
- **MongoDB Integration**: Automatically uploads data to MongoDB Atlas
- **CSV Export**: Saves data locally in CSV format
- **Progress Tracking**: Real-time progress updates and error reporting

## 📋 Requirements

- Python 3.7+
- Google Chrome browser
- ChromeDriver (automatically managed by Selenium)
- MongoDB Atlas account (optional, for database storage)
- Stable internet connection

## 🚀 Installation & Setup

### 1. Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd rimowa-scraper

# Or simply download the test9.py file
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install selenium beautifulsoup4 pandas pymongo
```

**Alternative**: Create a `requirements.txt` file:
```txt
selenium==4.33.0
beautifulsoup4==4.13.4
pandas==2.2.3
pymongo==4.10.1
```

Then install with:
```bash
pip install -r requirements.txt
```

### 4. MongoDB Setup (Optional)

If you want to use MongoDB storage:

1. **Create MongoDB Atlas Account**: Visit [MongoDB Atlas](https://www.mongodb.com/atlas) and create a free account
2. **Create a Cluster**: Set up a free cluster
3. **Get Connection String**: Copy your connection string from the Atlas dashboard
4. **Whitelist IP**: Add your IP address to the network access list
5. **Update Script**: Replace the `MONGODB_CONNECTION` string in `test9.py` with your connection string

```python
MONGODB_CONNECTION = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
```

## 🔧 Configuration

The script includes several configurable options at the top of the file:

```python
# MongoDB Configuration
MONGODB_CONNECTION = "your-mongodb-connection-string"
DB_NAME = "rimowa_luggage"
COLLECTION_UNIQUE = "rimowa"
COLLECTION_ALL = "rimowa_all"
```

**Categories scraped**:
- Cabin size luggage
- Check-in size luggage  
- Trunk/large luggage
- All luggage (comprehensive)

## 📖 Usage

### Basic Usage

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the scraper
python test9.py
```

### Expected Output

The script will:
1. Display progress as it collects product URLs from each category
2. Show real-time scraping progress for each product
3. Save two CSV files locally:
   - `rimowa_all_products.csv` - All product variants (includes duplicates)
   - `rimowa_unique_products.csv` - Unique products only
4. Upload data to MongoDB (if configured)
5. Display summary statistics

### Sample Output

```
🔍 Starting Rimowa product scraper...
============================================================

📂 Collecting links from Cabin category...
  Found 52 products

📂 Collecting links from Check-In category...
  Found 48 products

📊 Total links collected: 200
============================================================

🕷️ Scraping product pages...

[1/200] Scraping: https://www.rimowa.com/us/en/luggage/cabin/original/...
  ✓ Extracted 3 variants - Dims: 55 x 40 x 23 cm, Weight: 4.3 kg

📊 Scraping complete! Total product variants: 450
============================================================

💾 Writing CSV files...
✓ Created: rimowa_all_products.csv
✓ Created: rimowa_unique_products.csv

🔄 Starting MongoDB upload...
============================================================
✓ MongoDB connection verified
✓ Upload complete: 425 new, 25 updated

✅ All operations completed successfully!
```

## 📊 Data Structure

### CSV Columns

| Column | Description |
|--------|-------------|
| Product URL | Direct link to product page |
| Product Name | Full product name |
| Variant Size | Size variant (if multiple sizes) |
| Price | Product price in USD |
| Dimensions (cm) | Dimensions in centimeters |
| Dimensions (in) | Dimensions in inches |
| Weight (kg) | Weight in kilograms |
| Weight (lbs) | Weight in pounds |
| Colors | Available color options |
| Material | Product material (Aluminum, Polycarbonate, etc.) |
| SKU | Product SKU/model number |
| Category | Product category (Luggage) |
| Subcategory | Size category (Cabin, Check-In, Trunk, All) |
| Main Image URL | Primary product image URL |

### MongoDB Collections

- **rimowa**: Unique products only
- **rimowa_all**: All product variants including duplicates

Additional MongoDB fields:
- `last_updated`: Timestamp of last update
- `source`: Data source identifier
- `price_numeric`: Numeric price value for queries

## ⚠️ Troubleshooting

### Common Issues

**1. ChromeDriver Issues**
```bash
# Update Selenium (includes automatic ChromeDriver management)
pip install --upgrade selenium
```

**2. MongoDB Connection Errors**
- Verify your connection string is correct
- Check that your IP is whitelisted in MongoDB Atlas
- Ensure internet connectivity
- The script will continue and save CSV files even if MongoDB fails

**3. Scraping Blocked/Rate Limited**
- The script includes delays to be respectful to the website
- If blocked, wait a few hours before retrying
- Consider running during off-peak hours

**4. Missing Data**
- Some products may not have complete specifications
- The script uses multiple fallback methods to extract data
- Missing data is marked as empty strings in CSV

### Debug Mode

To see more detailed output, you can modify the script to include debug prints or run with verbose Python output:

```bash
python -v test9.py
```

## 🔄 Updates & Maintenance

- **Website Changes**: If Rimowa updates their website structure, the CSS selectors may need updating
- **Dependencies**: Keep dependencies updated for security and compatibility
- **MongoDB Schema**: The database schema can be extended by modifying the upload function

## 📝 Legal Notice

This scraper is for educational and research purposes. Please:
- Respect Rimowa's robots.txt and terms of service
- Use reasonable delays between requests
- Don't overload their servers
- Consider contacting Rimowa for official API access for commercial use

## 🤝 Support

If you encounter issues:
1. Check that all dependencies are installed correctly
2. Verify your virtual environment is activated
3. Ensure Chrome browser is installed and updated
4. For MongoDB issues, verify your Atlas setup

---

**Happy Scraping!** 🎒✈️ 
