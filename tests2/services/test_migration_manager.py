"""
Tests for the Migration Manager.

This module tests migration discovery, applied migration tracking,
and pending migration detection.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

from nes2.services.migration import Migration, MigrationManager


@pytest.fixture
def temp_migrations_dir():
    """Create a temporary migrations directory with test migrations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migrations_dir = Path(tmpdir) / "migrations"
        migrations_dir.mkdir()
        
        # Create migration 000-test-migration
        migration_000 = migrations_dir / "000-test-migration"
        migration_000.mkdir()
        
        # Create migrate.py with metadata
        (migration_000 / "migrate.py").write_text("""
AUTHOR = "test@example.com"
DATE = "2024-01-20"
DESCRIPTION = "Test migration for unit tests"

async def migrate(context):
    context.log("Test migration executed")
""")
        
        # Create README.md
        (migration_000 / "README.md").write_text("# Test Migration\n\nThis is a test.")
        
        # Create migration 001-another-migration
        migration_001 = migrations_dir / "001-another-migration"
        migration_001.mkdir()
        
        (migration_001 / "migrate.py").write_text("""
AUTHOR = "test2@example.com"
DATE = "2024-01-21"
DESCRIPTION = "Another test migration"

async def migrate(context):
    context.log("Another test migration executed")
""")
        
        (migration_001 / "README.md").write_text("# Another Migration\n\nAnother test.")
        
        yield migrations_dir


@pytest.fixture
def temp_db_repo():
    """Create a temporary database repository with Git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_repo = Path(tmpdir) / "nes-db"
        db_repo.mkdir()
        
        # Initialize Git repository
        subprocess.run(["git", "init"], cwd=db_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=db_repo,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=db_repo,
            check=True,
            capture_output=True
        )
        
        # Create initial commit
        (db_repo / "README.md").write_text("# Test Database\n")
        subprocess.run(["git", "add", "."], cwd=db_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=db_repo,
            check=True,
            capture_output=True
        )
        
        yield db_repo


@pytest.mark.asyncio
async def test_discover_migrations(temp_migrations_dir, temp_db_repo):
    """Test that migrations are discovered and sorted correctly."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    migrations = await manager.discover_migrations()
    
    assert len(migrations) == 2
    assert migrations[0].prefix == 0
    assert migrations[0].name == "test-migration"
    assert migrations[0].full_name == "000-test-migration"
    assert migrations[0].author == "test@example.com"
    assert migrations[0].description == "Test migration for unit tests"
    
    assert migrations[1].prefix == 1
    assert migrations[1].name == "another-migration"
    assert migrations[1].full_name == "001-another-migration"


@pytest.mark.asyncio
async def test_get_applied_migrations_empty(temp_migrations_dir, temp_db_repo):
    """Test getting applied migrations when none have been applied."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    applied = await manager.get_applied_migrations()
    
    assert applied == []


@pytest.mark.asyncio
async def test_get_applied_migrations_with_commits(temp_migrations_dir, temp_db_repo):
    """Test getting applied migrations from Git history."""
    # Create a migration commit in the database repository
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nTest migration applied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    applied = await manager.get_applied_migrations()
    
    assert len(applied) == 1
    assert "000-test-migration" in applied


@pytest.mark.asyncio
async def test_get_applied_migrations_with_batch_commits(temp_migrations_dir, temp_db_repo):
    """Test that batch commits are handled correctly (no duplicates)."""
    # Create multiple batch commits for the same migration
    for i in range(1, 4):
        (temp_db_repo / f"batch{i}.json").write_text(f'{{"batch": {i}}}')
        subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
        subprocess.run(
            [
                "git", "commit", "-m",
                f"Migration: 000-test-migration (Batch {i}/3)\n\nBatch commit"
            ],
            cwd=temp_db_repo,
            check=True,
            capture_output=True
        )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    applied = await manager.get_applied_migrations()
    
    # Should only have one entry despite 3 commits
    assert len(applied) == 1
    assert "000-test-migration" in applied


@pytest.mark.asyncio
async def test_get_pending_migrations(temp_migrations_dir, temp_db_repo):
    """Test getting pending migrations."""
    # Apply one migration
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nApplied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    pending = await manager.get_pending_migrations()
    
    # Should have one pending migration (001)
    assert len(pending) == 1
    assert pending[0].full_name == "001-another-migration"


@pytest.mark.asyncio
async def test_is_migration_applied(temp_migrations_dir, temp_db_repo):
    """Test checking if a specific migration is applied."""
    # Apply migration 000
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nApplied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    migrations = await manager.discover_migrations()
    
    # Check migration 000 (should be applied)
    is_applied_000 = await manager.is_migration_applied(migrations[0])
    assert is_applied_000 is True
    
    # Check migration 001 (should not be applied)
    is_applied_001 = await manager.is_migration_applied(migrations[1])
    assert is_applied_001 is False


@pytest.mark.asyncio
async def test_cache_clearing(temp_migrations_dir, temp_db_repo):
    """Test that cache clearing works correctly."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    # First call - should query Git
    applied1 = await manager.get_applied_migrations()
    assert applied1 == []
    
    # Add a migration commit
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nApplied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    # Second call without clearing cache - should return cached empty list
    applied2 = await manager.get_applied_migrations()
    assert applied2 == []
    
    # Clear cache and query again - should see the new migration
    manager.clear_cache()
    applied3 = await manager.get_applied_migrations()
    assert len(applied3) == 1
    assert "000-test-migration" in applied3


@pytest.mark.asyncio
async def test_get_migration_by_name(temp_migrations_dir, temp_db_repo):
    """Test getting a migration by its full name."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    
    migration = await manager.get_migration_by_name("000-test-migration")
    
    assert migration is not None
    assert migration.full_name == "000-test-migration"
    assert migration.prefix == 0
    assert migration.name == "test-migration"
    
    # Test non-existent migration
    missing = await manager.get_migration_by_name("999-does-not-exist")
    assert missing is None
