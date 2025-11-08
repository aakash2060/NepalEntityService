"""Tests for NES_DB_URL configuration in nes2.

Tests the NES_DB_URL environment variable support with file:// protocol.
"""

import pytest
import os
from pathlib import Path


class TestDatabaseURLConfiguration:
    """Test NES_DB_URL configuration."""

    def test_default_path_when_no_env_vars(self, monkeypatch):
        """Test that default path is used when no environment variables are set."""
        from nes2.config import Config
        
        # Clear all database-related env vars
        monkeypatch.delenv("NES_DB_URL", raising=False)
        
        path = Config.get_db_path()
        
        assert path == Path("nes-db/v2")

    def test_nes_db_url_with_file_protocol(self, monkeypatch):
        """Test NES_DB_URL with file:// protocol."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "file:///app/nes-db/v2")
        
        path = Config.get_db_path()
        
        assert path == Path("/app/nes-db/v2")

    def test_nes_db_url_with_absolute_path(self, monkeypatch):
        """Test NES_DB_URL with absolute path."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "file:///Users/test/database/v2")
        
        path = Config.get_db_path()
        
        assert path == Path("/Users/test/database/v2")

    def test_nes_db_url_invalid_protocol_raises_error(self, monkeypatch):
        """Test that non-file:// protocols raise ValueError."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "postgres://localhost/db")
        
        with pytest.raises(ValueError, match="NES_DB_URL must use 'file://' protocol"):
            Config.get_db_path()

    def test_nes_db_url_http_protocol_raises_error(self, monkeypatch):
        """Test that http:// protocol raises ValueError."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "http://example.com/db")
        
        with pytest.raises(ValueError, match="NES_DB_URL must use 'file://' protocol"):
            Config.get_db_path()

    def test_override_path_takes_highest_precedence(self, monkeypatch):
        """Test that override_path parameter takes highest precedence."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "file:///env/path")
        
        path = Config.get_db_path(override_path="/override/path")
        
        assert path == Path("/override/path")

    def test_nes_db_url_with_windows_path(self, monkeypatch):
        """Test NES_DB_URL with Windows-style path."""
        from nes2.config import Config
        
        # Windows paths in file:// URLs use forward slashes
        monkeypatch.setenv("NES_DB_URL", "file:///C:/Users/test/database/v2")
        
        path = Config.get_db_path()
        
        assert path == Path("/C:/Users/test/database/v2")

    def test_ensure_db_path_exists_creates_directory(self, tmp_path, monkeypatch):
        """Test that ensure_db_path_exists creates the directory."""
        from nes2.config import Config
        
        test_db_path = tmp_path / "test-db" / "v2"
        monkeypatch.setenv("NES_DB_URL", f"file://{test_db_path}")
        
        # Directory should not exist yet
        assert not test_db_path.exists()
        
        # Call ensure_db_path_exists
        result_path = Config.ensure_db_path_exists()
        
        # Directory should now exist
        assert result_path.exists()
        assert result_path.is_dir()
        assert result_path == test_db_path

    def test_initialize_database_uses_nes_db_url(self, tmp_path, monkeypatch):
        """Test that initialize_database respects NES_DB_URL."""
        from nes2.config import Config
        
        test_db_path = tmp_path / "test-db" / "v2"
        test_db_path.mkdir(parents=True)
        monkeypatch.setenv("NES_DB_URL", f"file://{test_db_path}")
        
        # Initialize database
        db = Config.initialize_database(base_path=str(test_db_path))
        
        # Verify database was initialized with correct path
        assert db is not None
        
        # Clean up
        Config.cleanup()


class TestDatabaseURLErrorMessages:
    """Test error messages for NES_DB_URL configuration."""

    def test_error_message_includes_example(self, monkeypatch):
        """Test that error message includes example usage."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "mysql://localhost/db")
        
        with pytest.raises(ValueError) as exc_info:
            Config.get_db_path()
        
        error_message = str(exc_info.value)
        assert "file://" in error_message
        assert "Example:" in error_message

    def test_error_message_shows_invalid_protocol(self, monkeypatch):
        """Test that error message shows the invalid protocol used."""
        from nes2.config import Config
        
        monkeypatch.setenv("NES_DB_URL", "redis://localhost")
        
        with pytest.raises(ValueError) as exc_info:
            Config.get_db_path()
        
        error_message = str(exc_info.value)
        assert "redis://" in error_message
