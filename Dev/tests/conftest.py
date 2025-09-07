import os
import sys
import tempfile
import shutil
import sqlite3
import json
from datetime import datetime
import pytest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_db(temp_dir):
    """Create a mock SQLite database with test data."""
    db_path = os.path.join(temp_dir, 'test_state.vscdb')
    conn = sqlite3.connect(db_path)
    
    # Create the cursorDiskKV table
    conn.execute('''
        CREATE TABLE cursorDiskKV (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Insert test data
    test_threads = [
        {
            'key': 'composerData:test-thread-1',
            'value': json.dumps({
                'createdAt': int(datetime(2025, 1, 15, 10, 30).timestamp() * 1000),
                'title': 'Test Thread 1'
            })
        },
        {
            'key': 'composerData:test-thread-2', 
            'value': json.dumps({
                'createdAt': int(datetime(2025, 1, 15, 14, 45).timestamp() * 1000),
                'title': 'Test Thread 2'
            })
        }
    ]
    
    test_bubbles = [
        {
            'key': 'bubbleId:test-thread-1:bubble-1',
            'value': json.dumps({
                'type': 1,  # user
                'content': 'Hello, this is a test message from user.',
                'createdAt': int(datetime(2025, 1, 15, 10, 31).timestamp() * 1000)
            })
        },
        {
            'key': 'bubbleId:test-thread-1:bubble-2',
            'value': json.dumps({
                'type': 2,  # assistant
                'content': 'Hello! This is a test response from assistant.',
                'createdAt': int(datetime(2025, 1, 15, 10, 32).timestamp() * 1000)
            })
        },
        {
            'key': 'bubbleId:test-thread-2:bubble-1',
            'value': json.dumps({
                'type': 1,  # user
                'content': 'Another test message.',
                'createdAt': int(datetime(2025, 1, 15, 14, 46).timestamp() * 1000)
            })
        }
    ]
    
    for item in test_threads + test_bubbles:
        conn.execute('INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)', 
                    (item['key'], item['value']))
    
    conn.commit()
    conn.close()
    
    yield db_path

@pytest.fixture
def output_dir(temp_dir):
    """Create output directory for tests."""
    output_path = os.path.join(temp_dir, 'test_output')
    os.makedirs(output_path, exist_ok=True)
    return output_path

