import os
import re
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
DB_PATH = os.path.join(WORKSPACE_DIR, "census_data.db")
CSV_DIR = os.path.join(WORKSPACE_DIR, "data")

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "artifacts"), exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "notes"), exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "code"), exist_ok=True)
os.makedirs(os.path.join(WORKSPACE_DIR, "history"), exist_ok=True)

files = {
    "Karnataka": "PC11_PCA_Data_Highlights_Karnataka.md",
    "Odisha": "PC11_PCA_Data_Highlights_Odisha.md",
    "Madhya Pradesh": "PCA Data Highlights MP.md"
}

def clean_cell(text):
    if not text:
        return ""
    # Remove markdown bold/italic
    text = re.sub(r"\*\*|\*", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()

def parse_markdown_pages(content, filename, state_name):
    # Split by page comments: <!-- page X -->
    pages = []
    
    # We find all matches and their indices
    matches = list(re.finditer(r"<!--\s*page\s+(\d+)\s*-->", content, re.IGNORECASE))
    
    if not matches:
        # If no page markers, treat entire file as page 1
        pages.append({
            "state": state_name,
            "file_name": filename,
            "page_number": 1,
            "content": content
        })
        return pages
        
    # Process text before the first page marker
    first_start = matches[0].start()
    first_text = content[:first_start].strip()
    if first_text:
        pages.append({
            "state": state_name,
            "file_name": filename,
            "page_number": 1,  # Pre-page 2 content is usually page 1 (cover)
            "content": first_text
        })
        
    for i in range(len(matches)):
        start = matches[i].end()
        end = matches[i+1].start() if i + 1 < len(matches) else len(content)
        page_num = int(matches[i].group(1))
        page_text = content[start:end].strip()
        pages.append({
            "state": state_name,
            "file_name": filename,
            "page_number": page_num,
            "content": page_text
        })
        
    return pages

def extract_tables_from_file(content, state_name):
    lines = content.split("\n")
    tables = []
    current_table_lines = []
    current_header_text = ""
    current_page = 1
    
    for i, line in enumerate(lines):
        # Check if page indicator
        page_match = re.match(r"<!--\s*page\s+(\d+)\s*-->", line, re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            
        # Update current header text if we find a header-like line above the table
        if not line.startswith("|") and line.strip():
            # If it's a heading, or a clean line, save it
            clean_line = line.strip()
            if clean_line.startswith("#") or clean_line.startswith("**") or (len(clean_line) < 100 and ":" in clean_line):
                current_header_text = clean_cell(clean_line)
                
        if line.startswith("|"):
            current_table_lines.append(line)
        else:
            if current_table_lines:
                # Process the table
                table_data = parse_table_lines(current_table_lines, current_header_text, current_page, state_name)
                if table_data:
                    tables.append(table_data)
                current_table_lines = []
                
    # Parse last table if exists
    if current_table_lines:
        table_data = parse_table_lines(current_table_lines, current_header_text, current_page, state_name)
        if table_data:
            tables.append(table_data)
            
    return tables

def parse_table_lines(lines, header_text, page, state_name):
    if len(lines) < 3: # Need at least header, alignment, and data row
        return None
        
    rows = []
    for line in lines:
        cells = [clean_cell(c) for c in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)
            
    if not rows:
        return None
        
    # Check if there are district data rows in the table
    # A district data row starts with a numeric code (length 3, e.g. 555) in the first column, and a text district name in the second
    district_rows = []
    headers = []
    
    # We try to separate headers from data rows
    data_started = False
    for r in rows:
        if not r or len(r) < 2:
            continue
        first_cell = r[0]
        # Skip alignment row (starts with dashes)
        if re.match(r"^[-:| ]+$", first_cell):
            continue
            
        is_district = False
        is_state_total = False
        
        # Check if first cell is a district code
        if first_cell.isdigit():
            val = int(first_cell)
            if 100 <= val <= 999: # 3-digit district code
                is_district = True
            elif val in (21, 23, 29): # State codes (Odisha, MP, Karnataka)
                is_state_total = True
        elif first_cell == "-" and r[1].upper() in ("KARNATAKA", "ODISHA", "MADHYA PRADESH"):
            is_state_total = True
            
        if is_district or is_state_total:
            data_started = True
            district_rows.append({
                "is_state": is_state_total,
                "code": first_cell if is_state_total else int(first_cell),
                "name": r[1],
                "cells": r[2:]
            })
        else:
            if not data_started:
                headers.append(r)
                
    if not district_rows:
        return None # Not a district data table
        
    return {
        "state": state_name,
        "page": page,
        "title": header_text,
        "headers": headers,
        "rows": district_rows
    }

def clean_numeric_value(val):
    if not val:
        return None
    val = val.strip().replace(",", "")
    if val == "-" or val == "" or val.lower() == "nil":
        return None
    # Try converting to float
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val

def build_master_table(all_tables):
    # We will build a unified master table by extracting core indicators
    # We can match tables by titles (case-insensitive)
    districts = {} # (state, district_name) -> metrics dict
    
    def get_district_record(state, name, code):
        key = (state, name.lower().strip())
        if key not in districts:
            districts[key] = {
                "state": state,
                "district_code": code,
                "district_name": name.strip(),
            }
        return districts[key]
        
    for table in all_tables:
        title = table["title"].lower()
        state = table["state"]
        
        # Determine table type based on title keywords
        is_pop = "population and decadal change by residence" in title or "population size and decadal change" in title or "statement 1" in title
        is_sex = "sex ratio" in title and "child" not in title and ("statement 6" in title or "statement - 6" in title or "page 31" in title or "page 14" in title)
        is_child_sex = "child sex ratio" in title or "statement 10" in title
        is_literacy = "literates and literacy rate by residence" in title and "persons" in title or "statement 19" in title or "page 52" in title
        is_workers = "total workers and work participation rate" in title and "persons" in title or "statement 22" in title or "page 58" in title
        is_sc = "scheduled caste" in title and "percentage" in title or "statement 14" in title
        is_st = "scheduled tribe" in title and "percentage" in title or "statement 18" in title
        is_density = "density of population" in title or "statement 4" in title
        
        # Category of workers
        is_cultivators = "cultivators and percentage" in title and "persons" in title or "statement 31" in title
        is_agri = "agricultural labourers" in title and "persons" in title or "statement 34" in title
        is_hhi = "household industry" in title and "persons" in title or "statement 37" in title
        is_other = "other workers" in title and "persons" in title or "statement 40" in title
        
        for row in table["rows"]:
            if row["is_state"]:
                continue # Skip state summary for district master table
                
            rec = get_district_record(state, row["name"], row["code"])
            cells = [clean_numeric_value(c) for c in row["cells"]]
            
            if is_pop and len(cells) >= 6:
                # cells: [pop_total, pop_rural, pop_urban, growth_total, growth_rural, growth_urban]
                rec["population_total"] = cells[0]
                rec["population_rural"] = cells[1]
                rec["population_urban"] = cells[2]
                rec["decadal_growth_total"] = cells[3]
                rec["decadal_growth_rural"] = cells[4]
                rec["decadal_growth_urban"] = cells[5]
                
            elif is_density and len(cells) >= 2:
                # cells: [density_2001, density_2011]
                rec["density_2011"] = cells[1]
                
            elif is_sex and len(cells) >= 6:
                # cells: [sr_total_2001, sr_total_2011, sr_rural_2001, sr_rural_2011, sr_urban_2001, sr_urban_2011]
                # Note: depending on columns, Col 3 and Col 4 are usually total 2001 and 2011
                # Let's check:
                # MP: | 418 | Sheopur | 858 | 897 | 857 | 892 | 863 | 920 |
                rec["sex_ratio_total_2001"] = cells[0]
                rec["sex_ratio_total_2011"] = cells[1]
                rec["sex_ratio_rural_2011"] = cells[3]
                rec["sex_ratio_urban_2011"] = cells[5]
                
            elif is_child_sex and len(cells) >= 6:
                rec["child_sex_ratio_total_2001"] = cells[0]
                rec["child_sex_ratio_total_2011"] = cells[1]
                rec["child_sex_ratio_rural_2011"] = cells[3]
                rec["child_sex_ratio_urban_2011"] = cells[5]
                
            elif is_sc and len(cells) >= 2:
                rec["sc_percentage_total_2011"] = cells[1] if len(cells) > 1 else cells[0]
                
            elif is_st and len(cells) >= 2:
                rec["st_percentage_total_2011"] = cells[1] if len(cells) > 1 else cells[0]
                
            elif is_literacy and len(cells) >= 6:
                # cells: [lit_total, lit_rural, lit_urban, rate_total, rate_rural, rate_urban]
                rec["literates_total"] = cells[0]
                rec["literacy_rate_total"] = cells[3]
                rec["literacy_rate_rural"] = cells[4]
                rec["literacy_rate_urban"] = cells[5]
                
            elif is_workers and len(cells) >= 6:
                rec["workers_total"] = cells[0]
                rec["wpr_total"] = cells[3]
                rec["wpr_rural"] = cells[4]
                rec["wpr_urban"] = cells[5]
                
            elif is_cultivators and len(cells) >= 6:
                # cells: [total, rural, urban, total_pct, rural_pct, urban_pct]
                rec["cultivators_percentage"] = cells[3]
                
            elif is_agri and len(cells) >= 6:
                rec["agricultural_labourers_percentage"] = cells[3]
                
            elif is_hhi and len(cells) >= 6:
                rec["household_industry_percentage"] = cells[3]
                
            elif is_other and len(cells) >= 6:
                rec["other_workers_percentage"] = cells[3]

    # Convert to DataFrame
    df = pd.DataFrame(list(districts.values()))
    
    # Fill in some defaults/placeholders if statements were missed or headers varied slightly
    # Let's ensure columns exist
    required_cols = [
        "state", "district_code", "district_name", 
        "population_total", "population_rural", "population_urban",
        "decadal_growth_total", "decadal_growth_rural", "decadal_growth_urban",
        "density_2011", "sex_ratio_total_2011", "sex_ratio_rural_2011", "sex_ratio_urban_2011",
        "child_sex_ratio_total_2011", "child_sex_ratio_rural_2011", "child_sex_ratio_urban_2011",
        "sc_percentage_total_2011", "st_percentage_total_2011",
        "literacy_rate_total", "literacy_rate_rural", "literacy_rate_urban",
        "wpr_total", "wpr_rural", "wpr_urban",
        "cultivators_percentage", "agricultural_labourers_percentage",
        "household_industry_percentage", "other_workers_percentage"
    ]
    
    for c in required_cols:
        if c not in df.columns:
            df[c] = None
            
    # Reorder
    df = df[required_cols]
    
    # Sort
    df = df.sort_values(by=["state", "district_name"])
    return df

def save_individual_tables(all_tables):
    for idx, table in enumerate(all_tables):
        state = table["state"]
        page = table["page"]
        title = table["title"] or f"Table_{idx}"
        # Make clean filename
        clean_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
        clean_title = clean_title[:80] # Truncate long names
        
        state_dir = os.path.join(CSV_DIR, state)
        os.makedirs(state_dir, exist_ok=True)
        
        # Reconstruct table headers
        headers_list = table["headers"]
        rows_list = table["rows"]
        
        # If there are headers, we try to create column names
        # Standardizing rows:
        csv_rows = []
        for row in rows_list:
            r_dict = {
                "district_code": row["code"],
                "district_name": row["name"]
            }
            # Add cell values
            for c_idx, cell in enumerate(row["cells"]):
                r_dict[f"col_{c_idx}"] = cell
            csv_rows.append(r_dict)
            
        df_csv = pd.DataFrame(csv_rows)
        filename = f"page_{page}_{clean_title}.csv"
        csv_path = os.path.join(state_dir, filename)
        df_csv.to_csv(csv_path, index=False)

def main():
    print("Starting data prep...")
    
    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create pages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT,
        file_name TEXT,
        page_number INTEGER,
        content TEXT
    )
    """)
    
    # Clear existing pages
    cursor.execute("DELETE FROM pages")
    conn.commit()
    
    all_pages = []
    all_tables = []
    
    for state, filename in files.items():
        filepath = os.path.join(DATA_DIR, filename)
        print(f"Parsing {filepath}...")
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse pages
        pages = parse_markdown_pages(content, filename, state)
        all_pages.extend(pages)
        print(f"Extracted {len(pages)} pages.")
        
        # Parse tables
        tables = extract_tables_from_file(content, state)
        all_tables.extend(tables)
        print(f"Extracted {len(tables)} tables.")
        
    # Save pages to database
    for page in all_pages:
        cursor.execute("""
        INSERT INTO pages (state, file_name, page_number, content)
        VALUES (?, ?, ?, ?)
        """, (page["state"], page["file_name"], page["page_number"], page["content"]))
    conn.commit()
    print(f"Saved {len(all_pages)} pages to database.")
    
    # Build and save master table
    master_df = build_master_table(all_tables)
    master_csv_path = os.path.join(CSV_DIR, "census_master.csv")
    master_df.to_csv(master_csv_path, index=False)
    print(f"Saved master district table to {master_csv_path} with {len(master_df)} districts.")
    
    # Save master table to SQLite
    master_df.to_sql("districts", conn, if_exists="replace", index=False)
    print("Saved districts master table to SQLite database.")
    
    # Save individual tables as CSVs
    save_individual_tables(all_tables)
    print("Saved individual tables as CSVs.")
    
    # Close connection
    conn.close()
    print("Data prep completed successfully!")

if __name__ == "__main__":
    main()
