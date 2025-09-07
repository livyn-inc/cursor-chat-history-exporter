import os
import json
import yaml
import shutil
import pytest
from unittest.mock import patch
from datetime import datetime

# Import functions to test
from update_latest_chat_per_date import (
    fetch_threads_for_date,
    main as update_main
)
from update_standalone_chat_per_date import (
    main as standalone_main
)

class TestDateFiltering:
    """Test date-based filtering functions."""
    
    def test_fetch_threads_for_date(self, mock_db):
        """Test fetching threads for a specific date."""
        from export_cursor_history import connect_db_readonly
        
        conn = connect_db_readonly(mock_db)
        
        # Test fetching threads for 2025-01-15
        threads = fetch_threads_for_date(conn, '2025-01-15')
        
        # Should get both test threads (both created on 2025-01-15)
        assert len(threads) == 2
        
        # Test fetching threads for a different date
        threads_empty = fetch_threads_for_date(conn, '2025-01-16')
        assert len(threads_empty) == 0
        
        conn.close()

class TestAIPMUpdate:
    """Test AIPM-style update functionality."""
    
    def test_update_latest_chat_per_date_flow_structure(self, mock_db, temp_dir):
        """Test updating chat data in Flow structure."""
        # Create Flow directory structure
        flow_root = os.path.join(temp_dir, 'Flow')
        date_path = os.path.join(flow_root, '202501', '2025-01-15')
        chats_dir = os.path.join(date_path, 'chats')
        os.makedirs(chats_dir, exist_ok=True)
        
        # Create some existing chat folders to be removed
        existing_folder = os.path.join(chats_dir, 'old_chat_folder')
        os.makedirs(existing_folder)
        with open(os.path.join(existing_folder, 'chat.yaml'), 'w') as f:
            f.write('old data')
        
        # Mock command line arguments
        test_args = [
            'update_latest_chat_per_date.py',
            '--date', '2025-01-15',
            '--db', mock_db,
            '--flow', flow_root
        ]
        
        with patch('sys.argv', test_args):
            update_main()
        
        # Check that old folder was removed
        assert not os.path.exists(existing_folder)
        
        # Check that new chat folders were created
        chat_folders = [d for d in os.listdir(chats_dir) 
                       if os.path.isdir(os.path.join(chats_dir, d)) and d.startswith('2025-01-15')]
        assert len(chat_folders) == 2
        
        # Check that each folder has a chat.yaml file
        for folder in chat_folders:
            yaml_file = os.path.join(chats_dir, folder, 'chat.yaml')
            assert os.path.exists(yaml_file)
            
            # Verify YAML content
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            assert 'threadId' in data
            assert 'messages' in data

class TestStandaloneUpdate:
    """Test standalone update functionality."""
    
    def test_update_standalone_chat_per_date(self, mock_db, temp_dir):
        """Test updating chat data in standalone structure."""
        output_root = os.path.join(temp_dir, 'chat_history')
        os.makedirs(output_root, exist_ok=True)
        
        # Create some existing chat folders for the target date
        existing_folder = os.path.join(output_root, '2025-01-15_10-00-00_old_chat_abc123')
        os.makedirs(existing_folder)
        with open(os.path.join(existing_folder, 'chat.yaml'), 'w') as f:
            f.write('old data')
        
        # Mock command line arguments
        test_args = [
            'update_standalone_chat_per_date.py',
            '--date', '2025-01-15',
            '--db', mock_db,
            '--out', output_root
        ]
        
        with patch('sys.argv', test_args):
            standalone_main()
        
        # Check that old folder was removed
        assert not os.path.exists(existing_folder)
        
        # Check that new chat folders were created
        chat_folders = [d for d in os.listdir(output_root) 
                       if os.path.isdir(os.path.join(output_root, d)) and d.startswith('2025-01-15')]
        assert len(chat_folders) == 2
        
        # Check that each folder has a chat.yaml file
        for folder in chat_folders:
            yaml_file = os.path.join(output_root, folder, 'chat.yaml')
            assert os.path.exists(yaml_file)

class TestErrorHandling:
    """Test error handling in update functions."""
    
    def test_invalid_date_format(self, mock_db, temp_dir):
        """Test handling of invalid date format."""
        flow_root = os.path.join(temp_dir, 'Flow')
        
        test_args = [
            'update_latest_chat_per_date.py',
            '--date', 'invalid-date',
            '--db', mock_db,
            '--flow', flow_root
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):  # Should exit with error
                update_main()
    
    def test_nonexistent_database(self, temp_dir):
        """Test handling of non-existent database."""
        flow_root = os.path.join(temp_dir, 'Flow')
        fake_db = os.path.join(temp_dir, 'nonexistent.db')
        
        test_args = [
            'update_latest_chat_per_date.py',
            '--date', '2025-01-15',
            '--db', fake_db,
            '--flow', flow_root
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises((FileNotFoundError, Exception)):
                update_main()

class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_yaml_format_compliance(self, mock_db, temp_dir):
        """Test that generated YAML files are properly formatted."""
        output_root = os.path.join(temp_dir, 'chat_history')
        os.makedirs(output_root, exist_ok=True)
        
        test_args = [
            'update_standalone_chat_per_date.py',
            '--date', '2025-01-15',
            '--db', mock_db,
            '--out', output_root
        ]
        
        with patch('sys.argv', test_args):
            standalone_main()
        
        # Find generated YAML files
        for root, dirs, files in os.walk(output_root):
            for file in files:
                if file == 'chat.yaml':
                    yaml_path = os.path.join(root, file)
                    
                    # Test that YAML can be loaded without errors
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Should start with ---
                    assert content.startswith('---\n')
                    
                    # Should be valid YAML
                    data = yaml.safe_load(content)
                    assert isinstance(data, dict)
                    
                    # Should have required fields
                    assert 'threadId' in data
                    assert 'created_at' in data
                    assert 'title20' in data
                    assert 'messages' in data
                    assert isinstance(data['messages'], list)
                    
                    # Each message should have role and content
                    for message in data['messages']:
                        assert 'role' in message
                        assert 'content' in message
                        assert message['role'] in ['user', 'assistant']
    
    def test_folder_naming_consistency(self, mock_db, temp_dir):
        """Test that folder names follow the expected pattern."""
        output_root = os.path.join(temp_dir, 'chat_history')
        os.makedirs(output_root, exist_ok=True)
        
        test_args = [
            'update_standalone_chat_per_date.py',
            '--date', '2025-01-15',
            '--db', mock_db,
            '--out', output_root
        ]
        
        with patch('sys.argv', test_args):
            standalone_main()
        
        # Check folder naming pattern: YYYY-MM-DD_HH-MM-SS_title20_threadId8
        chat_folders = [d for d in os.listdir(output_root) 
                       if os.path.isdir(os.path.join(output_root, d))]
        
        for folder in chat_folders:
            parts = folder.split('_')
            assert len(parts) >= 4  # date, time, title, threadId
            
            # Date part should be valid
            date_part = parts[0]
            assert len(date_part) == 10  # YYYY-MM-DD
            datetime.strptime(date_part, '%Y-%m-%d')  # Should not raise
            
            # Time part should be valid
            time_part = parts[1]
            assert len(time_part) == 8  # HH-MM-SS
            
            # Thread ID part should be 8 characters
            thread_id_part = parts[-1]
            assert len(thread_id_part) == 8

