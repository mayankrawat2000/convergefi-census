import os
import sqlite3
import pytest
from app.db import search_pages, read_page, DB_PATH

def test_db_initialized():
    # Verify DB file exists
    assert os.path.exists(DB_PATH)

def test_read_page():
    # Read page 1 of Karnataka
    content = read_page("Karnataka", 2)
    assert content is not None
    assert "Directorate of Census Operations" in content

def test_search_pages_success():
    # Search for Belgaum district
    res = search_pages("Belgaum", "Karnataka")
    assert len(res) > 0
    assert any("belgaum" in r["snippet"].lower() for r in res)
    assert all(r["state"] == "Karnataka" for r in res)

def test_search_pages_no_results():
    res = search_pages("nonexistentword123xyz")
    assert len(res) == 0
