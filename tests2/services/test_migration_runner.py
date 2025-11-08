"""
Tests for the Migration Runner.

This module tests migration script loading, execution, and batch processing.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

from nes2.services.migration import (
    Migration,
    MigrationManager,
    MigrationRunner,
    MigrationStatus,
)
from nes2.database.file_database import FileDatabase
from nes2.services.publication.service import PublicationService
from nes2.services.search.service import SearchService
from nes2.services.scraping.service import ScrapingService


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "db"
        db = FileDatabase(db_path)
        yield db


@pytest.fixture
def services(temp_db):
    """Create service instances for testing."""
    publication = PublicationService(temp_db)
    search = SearchService(temp_db)
    # ScrapingService is optional for migration runner tests
    # We'll pass None and migrations won't use it
    scraping = None
    
    return {
        'publication': publication,
        'search': search,
        'scraping': scraping,
        'db': temp_db
    }


@pytest.fixture
def temp_migrations_dir():
    """Create a temporary migrations directory with test migrations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migrations_dir = Path(tmpdir) / "migrations"
        migrations_dir.mkdir()
        
        # Create a simple test migration
        migration_000 = migrations_dir / "000-test-migration"
        migration_000.mkdir()
        
        # Create migrate.py with metadata
        (migration_000 / "migrate.py").write_text("""
AUTHOR = "test@example.com"
DATE = "2024-01-20"
DESCRIPTION = "Test migration for unit tests"

async def migrate(context):
    context.log("Test migration executed")
    context.log("Migration completed")
""")
        
        (migration_000 / "README.md").write_text("# Test Migration")
        
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
async def test_create_context(services, temp_migrations_dir, temp_db_repo):
    """Test that migration context is created correctly."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    context = runner.create_context(migration)
    
    assert context is not None
    assert context.publication == services['publication']
    assert context.search == services['search']
    assert context.scraping == services['scraping']
    assert context.db == services['db']
    assert context.migration_dir == migration.folder_path


@pytest.mark.asyncio
async def test_load_script_success(services, temp_migrations_dir, temp_db_repo):
    """Test loading a valid migration script."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    migrate_func, metadata = runner._load_script(migration)
    
    assert callable(migrate_func)
    assert metadata['author'] == "test@example.com"
    assert metadata['date'] == "2024-01-20"
    assert metadata['description'] == "Test migration for unit tests"


@pytest.mark.asyncio
async def test_load_script_missing_metadata(services, temp_migrations_dir, temp_db_repo):
    """Test that loading a script without metadata fails."""
    # Create a migration without metadata
    migration_bad = temp_migrations_dir / "001-bad-migration"
    migration_bad.mkdir()
    
    (migration_bad / "migrate.py").write_text("""
async def migrate(context):
    pass
""")
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    bad_migration = [m for m in migrations if m.name == "bad-migration"][0]
    
    with pytest.raises(ValueError, match="missing required metadata"):
        runner._load_script(bad_migration)


@pytest.mark.asyncio
async def test_run_migration_success(services, temp_migrations_dir, temp_db_repo):
    """Test running a migration successfully."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    result = await runner.run_migration(migration, dry_run=True, auto_commit=False)
    
    assert result.status == MigrationStatus.COMPLETED
    assert result.duration_seconds > 0
    assert len(result.logs) == 2
    assert "Test migration executed" in result.logs[0]
    assert result.error is None


@pytest.mark.asyncio
async def test_run_migration_skipped(services, temp_migrations_dir, temp_db_repo):
    """Test that already-applied migrations are skipped."""
    # Mark migration as applied by creating a commit
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nApplied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    result = await runner.run_migration(migration, dry_run=True, auto_commit=False)
    
    assert result.status == MigrationStatus.SKIPPED
    assert "already applied" in result.logs[0]


@pytest.mark.asyncio
async def test_run_migration_force(services, temp_migrations_dir, temp_db_repo):
    """Test that force flag allows re-execution of applied migrations."""
    # Mark migration as applied
    (temp_db_repo / "test.json").write_text('{"test": true}')
    subprocess.run(["git", "add", "."], cwd=temp_db_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: 000-test-migration\n\nApplied"],
        cwd=temp_db_repo,
        check=True,
        capture_output=True
    )
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    result = await runner.run_migration(
        migration,
        dry_run=True,
        auto_commit=False,
        force=True
    )
    
    assert result.status == MigrationStatus.COMPLETED
    assert any("Force re-execution" in log for log in result.logs)


@pytest.mark.asyncio
async def test_run_migrations_batch(services, temp_migrations_dir, temp_db_repo):
    """Test running multiple migrations in batch."""
    # Create a second migration
    migration_001 = temp_migrations_dir / "001-second-migration"
    migration_001.mkdir()
    
    (migration_001 / "migrate.py").write_text("""
AUTHOR = "test@example.com"
DATE = "2024-01-21"
DESCRIPTION = "Second test migration"

async def migrate(context):
    context.log("Second migration executed")
""")
    
    (migration_001 / "README.md").write_text("# Second Migration")
    
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    
    results = await runner.run_migrations(
        migrations,
        dry_run=True,
        auto_commit=False
    )
    
    assert len(results) == 2
    assert all(r.status == MigrationStatus.COMPLETED for r in results)
    assert results[0].migration.full_name == "000-test-migration"
    assert results[1].migration.full_name == "001-second-migration"


@pytest.mark.asyncio
async def test_commit_and_push_with_changes(services, temp_migrations_dir, temp_db_repo):
    """Test committing and pushing changes after migration."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    # Create some changes in the database repository
    test_file = temp_db_repo / "test_entity.json"
    test_file.write_text('{"id": "test", "name": "Test Entity"}')
    
    # Create a mock result
    from nes2.services.migration.models import MigrationResult
    result = MigrationResult(
        migration=migration,
        status=MigrationStatus.COMPLETED,
        duration_seconds=1.5,
        entities_created=1,
        relationships_created=0,
        error=None,
        logs=["Test migration completed"]
    )
    
    # Commit and push (dry_run=False to actually commit)
    await runner.commit_and_push(migration, result, dry_run=False)
    
    # Verify commit was created
    git_log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=temp_db_repo,
        capture_output=True,
        text=True,
        check=True
    )
    
    assert "Migration: 000-test-migration" in git_log.stdout
    
    # Verify the migration is now marked as applied
    applied = await manager.get_applied_migrations()
    assert "000-test-migration" in applied


@pytest.mark.asyncio
async def test_commit_and_push_no_changes(services, temp_migrations_dir, temp_db_repo):
    """Test that commit_and_push handles no changes gracefully."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    # Create a mock result
    from nes2.services.migration.models import MigrationResult
    result = MigrationResult(
        migration=migration,
        status=MigrationStatus.COMPLETED,
        duration_seconds=1.5,
        entities_created=0,
        relationships_created=0,
        error=None,
        logs=["Test migration completed"]
    )
    
    # Commit and push with no changes (should not fail)
    await runner.commit_and_push(migration, result, dry_run=False)
    
    # Verify no new commit was created (still just the initial commit)
    git_log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=temp_db_repo,
        capture_output=True,
        text=True,
        check=True
    )
    
    # Should only have the initial commit
    assert git_log.stdout.count('\n') == 1
    assert "Initial commit" in git_log.stdout


@pytest.mark.asyncio
async def test_format_commit_message(services, temp_migrations_dir, temp_db_repo):
    """Test that commit messages are formatted correctly."""
    manager = MigrationManager(temp_migrations_dir, temp_db_repo)
    runner = MigrationRunner(
        publication_service=services['publication'],
        search_service=services['search'],
        scraping_service=services['scraping'],
        db=services['db'],
        migration_manager=manager
    )
    
    migrations = await manager.discover_migrations()
    migration = migrations[0]
    
    # Create a mock result
    from nes2.services.migration.models import MigrationResult
    result = MigrationResult(
        migration=migration,
        status=MigrationStatus.COMPLETED,
        duration_seconds=1.5,
        entities_created=10,
        relationships_created=5,
        error=None,
        logs=[]
    )
    
    # Test single commit message
    message = runner._format_commit_message(migration, result)
    
    assert "Migration: 000-test-migration" in message
    assert "Author: test@example.com" in message
    assert "Date: 2024-01-20" in message
    assert "Entities created: 10" in message
    assert "Relationships created: 5" in message
    assert "Duration: 1.5s" in message
    
    # Test batch commit message
    message_batch = runner._format_commit_message(migration, result, batch_info=(1, 3))
    
    assert "Migration: 000-test-migration (Batch 1/3)" in message_batch
