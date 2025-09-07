import os
import json
import yaml
import pytest
from unittest.mock import patch, MagicMock

# Import functions to test
from export_cursor_history import (
    connect_db_readonly, 
    fetch_all_threads, 
    fetch_bubbles,
    group_messages_by_role,
    derive_title20,
    write_yaml,
    ensure_manifest,
    export_batch
)

class TestDatabaseFunctions:
    """Test database connection and data fetching functions."""
    
    def test_connect_db_readonly(self, mock_db):
        """Test database connection in read-only mode."""
        conn = connect_db_readonly(mock_db)
        assert conn is not None
        
        # Test that we can query the database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cursorDiskKV")
        count = cursor.fetchone()[0]
        assert count > 0
        conn.close()
    
    def test_fetch_all_threads(self, mock_db):
        """Test fetching all thread data."""
        conn = connect_db_readonly(mock_db)
        threads = fetch_all_threads(conn, order_desc=True)
        
        assert len(threads) == 2
        # Should be ordered by creation time (newest first)
        assert threads[0][0] == 'test-thread-2'  # Created later
        assert threads[1][0] == 'test-thread-1'  # Created earlier
        conn.close()
    
    def test_fetch_bubbles(self, mock_db):
        """Test fetching bubble messages for a thread."""
        conn = connect_db_readonly(mock_db)
        bubbles = fetch_bubbles(conn, 'test-thread-1')
        
        assert len(bubbles) == 2
        # Check that we got the expected messages
        bubble_contents = [json.loads(bubble[1])['content'] for bubble in bubbles]
        assert 'Hello, this is a test message from user.' in bubble_contents
        assert 'Hello! This is a test response from assistant.' in bubble_contents
        conn.close()

class TestMessageProcessing:
    """Test message processing and formatting functions."""
    
    def test_derive_title20(self):
        """Test title derivation from content."""
        # Normal case
        assert derive_title20("This is a test message") == "This is a test messa"
        
        # Short message
        assert derive_title20("Short") == "Short"
        
        # Empty or whitespace
        assert derive_title20("") == "untitled"
        assert derive_title20("   ") == "untitled"
        
        # With special characters (? becomes ？)
        assert derive_title20("Hello! How are you?") == "Hello! How are you？"
    
    def test_group_messages_by_role(self):
        """Test message grouping by role."""
        # Mock bubble data
        bubbles = [
            ('bubble-1', json.dumps({'type': 1, 'content': 'User message 1'})),
            ('bubble-2', json.dumps({'type': 1, 'content': 'User message 2'})),
            ('bubble-3', json.dumps({'type': 2, 'content': 'Assistant message 1'})),
            ('bubble-4', json.dumps({'type': 2, 'content': 'Assistant message 2'})),
            ('bubble-5', json.dumps({'type': 1, 'content': 'User message 3'})),
        ]
        
        grouped = group_messages_by_role(bubbles)
        
        # Should have 3 groups: user, assistant, user
        assert len(grouped) == 3
        
        # First group: combined user messages
        assert grouped[0]['role'] == 'user'
        assert 'User message 1' in grouped[0]['texts']
        assert 'User message 2' in grouped[0]['texts']
        
        # Second group: combined assistant messages
        assert grouped[1]['role'] == 'assistant'
        assert 'Assistant message 1' in grouped[1]['texts']
        assert 'Assistant message 2' in grouped[1]['texts']
        
        # Third group: single user message
        assert grouped[2]['role'] == 'user'
        assert 'User message 3' in grouped[2]['texts']

class TestFileOperations:
    """Test file writing and YAML operations."""
    
    def test_write_yaml(self, temp_dir):
        """Test writing chat data to YAML file."""
        folder_path = os.path.join(temp_dir, 'test_chat')
        thread_id = 'test-thread-1'
        created_at = '2025-01-15_10-30-15'
        title20 = 'Test Chat Title'
        
        grouped_messages = [
            {'role': 'user', 'texts': ['Hello, this is a test.']},
            {'role': 'assistant', 'texts': ['Hello! How can I help you?']}
        ]
        
        write_yaml(folder_path, thread_id, created_at, title20, grouped_messages)
        
        # Check that folder was created
        assert os.path.exists(folder_path)
        
        # Check that YAML file was created
        yaml_file = os.path.join(folder_path, 'chat.yaml')
        assert os.path.exists(yaml_file)
        
        # Check YAML content
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert data['threadId'] == thread_id
        assert data['created_at'] == created_at
        assert data['title20'] == title20
        assert len(data['messages']) == 2
        assert data['messages'][0]['role'] == 'user'
        assert data['messages'][1]['role'] == 'assistant'
        assert 'Hello, this is a test.' in data['messages'][0]['content']
        assert 'Hello! How can I help you?' in data['messages'][1]['content']

class TestManifestOperations:
    """Test manifest file operations."""
    
    def test_ensure_manifest(self, mock_db, output_dir):
        """Test manifest creation and content."""
        manifest_path = os.path.join(output_dir, 'export_manifest.json')
        conn = connect_db_readonly(mock_db)
        
        ensure_manifest(manifest_path, conn, order_desc=True)
        
        # Check that manifest file was created
        assert os.path.exists(manifest_path)
        
        # Check manifest content
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        assert 'items' in manifest
        assert len(manifest['items']) == 2
        
        # Check thread data structure
        thread = manifest['items'][0]
        assert 'cid' in thread
        assert 'createdAtMs' in thread
        assert 'processed' in thread
        assert thread['processed'] is False  # Initially not processed
        
        conn.close()

class TestExportBatch:
    """Test batch export functionality."""
    
    def test_export_batch_small(self, mock_db, output_dir):
        """Test exporting a small batch of threads."""
        manifest_path = os.path.join(output_dir, 'export_manifest.json')
        conn = connect_db_readonly(mock_db)
        
        # Create manifest first
        ensure_manifest(manifest_path, conn, order_desc=True)
        
        # Export batch
        done, skipped = export_batch(conn, output_dir, manifest_path, 0, 2)
        
        assert done == 2  # Both threads should be exported
        assert skipped == 0
        
        # Check that chat folders were created
        chat_folders = [d for d in os.listdir(output_dir) 
                       if os.path.isdir(os.path.join(output_dir, d)) and d.startswith('2025-01-15')]
        assert len(chat_folders) == 2
        
        # Check that each folder has a chat.yaml file
        for folder in chat_folders:
            yaml_file = os.path.join(output_dir, folder, 'chat.yaml')
            assert os.path.exists(yaml_file)
        
        conn.close()
    
    def test_export_batch_with_limit(self, mock_db, output_dir):
        """Test exporting with batch size limit."""
        manifest_path = os.path.join(output_dir, 'export_manifest.json')
        conn = connect_db_readonly(mock_db)
        
        # Create manifest first
        ensure_manifest(manifest_path, conn, order_desc=True)
        
        # Export only 1 thread
        done, skipped = export_batch(conn, output_dir, manifest_path, 0, 1)
        
        assert done == 1
        assert skipped == 0
        
        # Check that only 1 chat folder was created
        chat_folders = [d for d in os.listdir(output_dir) 
                       if os.path.isdir(os.path.join(output_dir, d)) and d.startswith('2025-01-15')]
        assert len(chat_folders) == 1
        
        conn.close()

class TestIntegration:
    """Integration tests for the full export process."""
    
    @patch('export_cursor_history.default_db_path')
    def test_main_function_all_option(self, mock_default_db, mock_db, output_dir, capsys):
        """Test main function with --all option."""
        mock_default_db.return_value = mock_db
        
        # Mock sys.argv to simulate command line arguments
        test_args = [
            'export_cursor_history.py',
            '--db', mock_db,
            '--out', output_dir,
            '--all',
            '--rescan'
        ]
        
        with patch('sys.argv', test_args):
            from export_cursor_history import main
            main()
        
        # Check output
        captured = capsys.readouterr()
        output_json = json.loads(captured.out)
        
        assert output_json['mode'] == 'all'
        assert output_json['total_threads'] == 2
        assert output_json['processed'] == 2
        assert output_json['skipped'] == 0
        
        # Check that files were created
        manifest_path = os.path.join(output_dir, 'export_manifest.json')
        assert os.path.exists(manifest_path)
        
        chat_folders = [d for d in os.listdir(output_dir) 
                       if os.path.isdir(os.path.join(output_dir, d)) and d.startswith('2025-01-15')]
        assert len(chat_folders) == 2

