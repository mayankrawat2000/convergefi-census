import os
import sqlite3
import re
from typing import List, Dict, Any, Optional

from app.config import WORKSPACE_DIR
DB_PATH = os.path.join(WORKSPACE_DIR, "census_data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def search_pages(query: str, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search page content in the database using multiple keywords.
    Returns a list of matching pages with snippets.
    """
    # Clean and extract keywords
    query_clean = re.sub(r'[^\w\s]', ' ', query)
    words = [w.strip() for w in query_clean.split() if w.strip()]
    if not words:
        return []
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query
    sql = "SELECT state, file_name, page_number, content FROM pages WHERE "
    conditions = []
    params = []
    
    for word in words:
        conditions.append("content LIKE ?")
        params.append(f"%{word}%")
        
    sql += " AND ".join(conditions)
    
    if state_filter:
        sql += " AND state = ?"
        params.append(state_filter)
        
    # Limit to top 15 results
    sql += " LIMIT 15"
    
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            content = row["content"]
            state = row["state"]
            page_number = row["page_number"]
            file_name = row["file_name"]
            
            # Generate snippet
            snippet = create_snippet(content, words)
            
            results.append({
                "state": state,
                "file_name": file_name,
                "page_number": page_number,
                "snippet": snippet,
                "content_preview": content[:300] + "..." if len(content) > 300 else content
            })
        return results
    except sqlite3.OperationalError as e:
        print(f"Database search error: {e}")
        return []
    finally:
        conn.close()

def read_page(state: str, page_number: int) -> Optional[str]:
    """
    Retrieve the full text content of a specific page.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT content FROM pages WHERE state = ? AND page_number = ?", 
            (state, page_number)
        )
        row = cursor.fetchone()
        return row["content"] if row else None
    finally:
        conn.close()

def create_snippet(content: str, keywords: List[str]) -> str:
    """
    Extract a snippet of text surrounding the first match of any keyword.
    """
    content_clean = content.replace("\n", " ")
    
    # Find position of first keyword match
    first_pos = -1
    matched_word = ""
    for word in keywords:
        pos = content_clean.lower().find(word.lower())
        if pos != -1:
            if first_pos == -1 or pos < first_pos:
                first_pos = pos
                matched_word = word
                
    if first_pos == -1:
        # Default to beginning of text
        return content_clean[:300] + "..." if len(content_clean) > 300 else content_clean
        
    # Extract window around match
    start = max(0, first_pos - 120)
    end = min(len(content_clean), first_pos + 120)
    
    snippet = content_clean[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content_clean):
        snippet = snippet + "..."
        
    return snippet
