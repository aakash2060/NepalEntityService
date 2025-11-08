"""
CLI commands for managing database migrations.

This module provides commands for:
- Listing all migrations with their status
- Showing pending migrations
- Running migrations
- Creating new migration folders from templates
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click

from nes2.config import Config
from nes2.services.migration import (
    MigrationManager,
    MigrationRunner,
    MigrationStatus,
)

logger = logging.getLogger(__name__)


@click.group()
def migrate():
    """Manage database migrations.
    
    Migrations are versioned folders containing Python scripts that apply
    data changes to the entity database. This command group provides tools
    for listing, running, and creating migrations.
    """
    pass


@migrate.command()
@click.option(
    '--migrations-dir',
    default='migrations',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to migrations directory'
)
@click.option(
    '--db-repo',
    default='nes-db',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to database repository'
)
def list(migrations_dir: str, db_repo: str):
    """List all migrations with their status.
    
    Shows all discovered migrations in the migrations/ directory along with
    their metadata (author, date, description) and whether they have been
    applied or are still pending.
    
    Examples:
        nes2 migrate list
        nes2 migrate list --migrations-dir ./migrations
    """
    async def do_list():
        # Initialize migration manager
        manager = MigrationManager(
            migrations_dir=Path(migrations_dir),
            db_repo_path=Path(db_repo)
        )
        
        # Discover all migrations
        migrations = await manager.discover_migrations()
        
        if not migrations:
            click.echo("No migrations found.")
            return
        
        # Get applied migrations
        applied = await manager.get_applied_migrations()
        
        # Display migrations
        click.echo(f"\n{'='*80}")
        click.echo(f"{'Migration':<30} {'Status':<12} {'Author':<20} {'Date':<12}")
        click.echo(f"{'='*80}")
        
        for migration in migrations:
            # Determine status
            is_applied = migration.full_name in applied
            status = "✓ Applied" if is_applied else "○ Pending"
            
            # Format fields
            name = migration.full_name
            author = migration.author or "Unknown"
            date = migration.date.strftime('%Y-%m-%d') if migration.date else "Unknown"
            
            # Truncate long fields
            if len(name) > 28:
                name = name[:25] + "..."
            if len(author) > 18:
                author = author[:15] + "..."
            
            click.echo(f"{name:<30} {status:<12} {author:<20} {date:<12}")
            
            # Show description if available
            if migration.description:
                desc = migration.description
                if len(desc) > 76:
                    desc = desc[:73] + "..."
                click.echo(f"  {desc}")
        
        click.echo(f"{'='*80}")
        
        # Summary
        total = len(migrations)
        applied_count = len([m for m in migrations if m.full_name in applied])
        pending_count = total - applied_count
        
        click.echo(f"\nTotal: {total} migrations ({applied_count} applied, {pending_count} pending)")
        click.echo()
    
    # Run async function
    asyncio.run(do_list())


@migrate.command()
@click.option(
    '--migrations-dir',
    default='migrations',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to migrations directory'
)
@click.option(
    '--db-repo',
    default='nes-db',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to database repository'
)
def pending(migrations_dir: str, db_repo: str):
    """Show only pending migrations.
    
    Lists migrations that have not yet been applied to the database.
    These are migrations that exist in the migrations/ directory but
    do not have corresponding persisted snapshots in the database repository.
    
    Examples:
        nes2 migrate pending
        nes2 migrate pending --migrations-dir ./migrations
    """
    async def do_pending():
        # Initialize migration manager
        manager = MigrationManager(
            migrations_dir=Path(migrations_dir),
            db_repo_path=Path(db_repo)
        )
        
        # Get pending migrations
        migrations = await manager.get_pending_migrations()
        
        if not migrations:
            click.echo("\n✓ No pending migrations. All migrations have been applied.\n")
            return
        
        # Display pending migrations
        click.echo(f"\n{'='*80}")
        click.echo(f"Pending Migrations ({len(migrations)})")
        click.echo(f"{'='*80}\n")
        
        for i, migration in enumerate(migrations, 1):
            click.echo(f"{i}. {migration.full_name}")
            
            if migration.author:
                click.echo(f"   Author: {migration.author}")
            
            if migration.date:
                click.echo(f"   Date: {migration.date.strftime('%Y-%m-%d')}")
            
            if migration.description:
                click.echo(f"   Description: {migration.description}")
            
            click.echo()
        
        click.echo(f"{'='*80}")
        click.echo(f"\nRun 'nes2 migrate run --all' to execute all pending migrations.")
        click.echo()
    
    # Run async function
    asyncio.run(do_pending())


@migrate.command()
@click.argument('migration_name', required=False)
@click.option(
    '--all',
    'run_all',
    is_flag=True,
    help='Run all pending migrations'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Execute migration without committing changes'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force re-execution of already-applied migrations'
)
@click.option(
    '--migrations-dir',
    default='migrations',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to migrations directory'
)
@click.option(
    '--db-repo',
    default='nes-db',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to database repository'
)
@click.option(
    '--db-path',
    default='nes-db/v2',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Path to database directory'
)
def run(
    migration_name: Optional[str],
    run_all: bool,
    dry_run: bool,
    force: bool,
    migrations_dir: str,
    db_repo: str,
    db_path: str
):
    """Run one or more migrations.
    
    Execute a specific migration by name, or run all pending migrations
    with the --all flag. Migrations modify the entity database and commit
    changes to the database repository.
    
    Examples:
        nes2 migrate run 000-initial-locations
        nes2 migrate run --all
        nes2 migrate run 001-update-names --dry-run
        nes2 migrate run 000-initial-locations --force
    """
    # Validate arguments
    if not migration_name and not run_all:
        click.echo(
            "Error: Must specify either a migration name or use --all flag.\n"
            "Examples:\n"
            "  nes2 migrate run 000-initial-locations\n"
            "  nes2 migrate run --all",
            err=True
        )
        raise click.Abort()
    
    if migration_name and run_all:
        click.echo(
            "Error: Cannot specify both a migration name and --all flag.",
            err=True
        )
        raise click.Abort()
    
    async def do_run():
        # Initialize database and services
        click.echo("Initializing database and services...")
        Config.initialize_database(base_path=db_path)
        db = Config.get_database()
        publication_service = Config.get_publication_service()
        search_service = Config.get_search_service()
        
        # Initialize scraping service (may not be configured, that's ok)
        try:
            from nes2.services.scraping.service import ScrapingService
            scraping_service = ScrapingService()
        except Exception as e:
            logger.warning(f"Scraping service not available: {e}")
            scraping_service = None
        
        # Initialize migration manager and runner
        manager = MigrationManager(
            migrations_dir=Path(migrations_dir),
            db_repo_path=Path(db_repo)
        )
        
        runner = MigrationRunner(
            publication_service=publication_service,
            search_service=search_service,
            scraping_service=scraping_service,
            db=db,
            migration_manager=manager
        )
        
        # Determine which migrations to run
        if run_all:
            migrations = await manager.get_pending_migrations()
            
            if not migrations:
                click.echo("\n✓ No pending migrations to run.\n")
                return
            
            click.echo(f"\nFound {len(migrations)} pending migration(s):\n")
            for migration in migrations:
                click.echo(f"  - {migration.full_name}")
            click.echo()
            
            if dry_run:
                click.echo("Running in DRY RUN mode (changes will not be committed)\n")
            
            # Confirm before running
            if not dry_run:
                click.confirm(
                    "Do you want to proceed with running these migrations?",
                    abort=True
                )
            
            # Run all migrations
            click.echo("\nExecuting migrations...\n")
            results = await runner.run_migrations(
                migrations=migrations,
                dry_run=dry_run,
                auto_commit=not dry_run,
                stop_on_failure=True
            )
            
            # Display results
            click.echo(f"\n{'='*80}")
            click.echo("Migration Results")
            click.echo(f"{'='*80}\n")
            
            for result in results:
                if result.status == MigrationStatus.COMPLETED:
                    click.echo(f"✓ {result.migration.full_name}")
                    click.echo(f"  Duration: {result.duration_seconds:.1f}s")
                    click.echo(f"  Entities created: {result.entities_created}")
                    click.echo(f"  Relationships created: {result.relationships_created}")
                elif result.status == MigrationStatus.SKIPPED:
                    click.echo(f"⊘ {result.migration.full_name} (skipped - already applied)")
                elif result.status == MigrationStatus.FAILED:
                    click.echo(f"✗ {result.migration.full_name} (FAILED)")
                    click.echo(f"  Error: {result.error}")
                
                click.echo()
            
            # Summary
            completed = sum(1 for r in results if r.status == MigrationStatus.COMPLETED)
            skipped = sum(1 for r in results if r.status == MigrationStatus.SKIPPED)
            failed = sum(1 for r in results if r.status == MigrationStatus.FAILED)
            
            click.echo(f"{'='*80}")
            click.echo(f"Summary: {completed} completed, {skipped} skipped, {failed} failed")
            click.echo(f"{'='*80}\n")
            
            # Exit with error if any failed
            if failed > 0:
                raise click.Abort()
        
        else:
            # Run single migration
            migration = await manager.get_migration_by_name(migration_name)
            
            if not migration:
                click.echo(
                    f"Error: Migration '{migration_name}' not found.",
                    err=True
                )
                raise click.Abort()
            
            # Check if already applied
            is_applied = await manager.is_migration_applied(migration)
            
            if is_applied and not force:
                click.echo(
                    f"\nMigration '{migration_name}' has already been applied.\n"
                    f"Use --force to re-execute it.\n"
                )
                return
            
            if force and is_applied:
                click.echo(
                    f"\nWARNING: Force re-executing already-applied migration "
                    f"'{migration_name}'\n"
                )
            
            if dry_run:
                click.echo(f"\nRunning migration '{migration_name}' in DRY RUN mode\n")
            else:
                click.echo(f"\nRunning migration '{migration_name}'...\n")
            
            # Run migration
            result = await runner.run_migration(
                migration=migration,
                dry_run=dry_run,
                auto_commit=not dry_run,
                force=force
            )
            
            # Display result
            click.echo(f"\n{'='*80}")
            
            if result.status == MigrationStatus.COMPLETED:
                click.echo(f"✓ Migration completed successfully")
                click.echo(f"\nDuration: {result.duration_seconds:.1f}s")
                click.echo(f"Entities created: {result.entities_created}")
                click.echo(f"Relationships created: {result.relationships_created}")
                
                if result.logs:
                    click.echo(f"\nLogs:")
                    for log in result.logs:
                        click.echo(f"  {log}")
            
            elif result.status == MigrationStatus.SKIPPED:
                click.echo(f"⊘ Migration skipped (already applied)")
            
            elif result.status == MigrationStatus.FAILED:
                click.echo(f"✗ Migration FAILED")
                click.echo(f"\nError: {result.error}")
                
                if result.logs:
                    click.echo(f"\nLogs:")
                    for log in result.logs:
                        click.echo(f"  {log}")
                
                click.echo(f"\n{'='*80}\n")
                raise click.Abort()
            
            click.echo(f"{'='*80}\n")
    
    # Run async function
    asyncio.run(do_run())


@migrate.command()
@click.argument('name')
@click.option(
    '--migrations-dir',
    default='migrations',
    type=click.Path(file_okay=False, dir_okay=True),
    help='Path to migrations directory'
)
@click.option(
    '--author',
    prompt='Author email',
    help='Author email address'
)
def create(name: str, migrations_dir: str, author: str):
    """Create a new migration folder from template.
    
    Generates a new migration folder with the next available prefix number
    and the specified descriptive name. The folder will contain template
    files for the migration script and README.
    
    Examples:
        nes2 migrate create add-ministers
        nes2 migrate create update-locations --author user@example.com
    """
    async def do_create():
        from datetime import datetime
        
        migrations_path = Path(migrations_dir)
        
        # Create migrations directory if it doesn't exist
        migrations_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize migration manager to discover existing migrations
        manager = MigrationManager(
            migrations_dir=migrations_path,
            db_repo_path=Path('nes-db')  # Not used for discovery
        )
        
        # Discover existing migrations to determine next prefix
        existing_migrations = await manager.discover_migrations()
        
        if existing_migrations:
            next_prefix = max(m.prefix for m in existing_migrations) + 1
        else:
            next_prefix = 0
        
        # Format migration name
        migration_name = f"{next_prefix:03d}-{name}"
        migration_folder = migrations_path / migration_name
        
        # Check if folder already exists
        if migration_folder.exists():
            click.echo(
                f"Error: Migration folder '{migration_name}' already exists.",
                err=True
            )
            raise click.Abort()
        
        # Create migration folder
        click.echo(f"\nCreating migration: {migration_name}")
        migration_folder.mkdir(parents=True)
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create migrate.py from template
        migrate_template = f'''"""
Migration: {migration_name}
Description: [TODO: Describe what this migration does]
Author: {author}
Date: {current_date}
"""

# Migration metadata (used for Git commit message)
AUTHOR = "{author}"
DATE = "{current_date}"
DESCRIPTION = "[TODO: Describe what this migration does]"


async def migrate(context):
    """
    Main migration function.
    
    Args:
        context: MigrationContext with access to services and data
        
    Available context attributes:
        - context.publication: PublicationService for creating/updating entities
        - context.search: SearchService for querying entities
        - context.scraping: ScrapingService for data extraction (if available)
        - context.db: EntityDatabase for direct read access
        - context.migration_dir: Path to this migration folder
        
    Available context methods:
        - context.read_csv(filename) -> List[Dict]
        - context.read_json(filename) -> Any
        - context.read_excel(filename, sheet_name=None) -> List[Dict]
        - context.log(message) -> None
    
    Example usage:
        # Read data from CSV
        data = context.read_csv("data.csv")
        
        # Create actor for this migration
        actor_id = "actor:migration:{migration_name}"
        
        # Process each row
        for row in data:
            entity = Entity(...)
            await context.publication.create_entity(
                entity=entity,
                actor_id=actor_id,
                change_description="Description of change"
            )
        
        context.log("Migration completed")
    """
    # TODO: Implement your migration logic here
    
    context.log("Migration started")
    
    # Example: Read data from CSV
    # data = context.read_csv("data.csv")
    
    # Example: Create actor for this migration
    # actor_id = "actor:migration:{migration_name}"
    
    # Example: Process each row
    # for row in data:
    #     entity = Entity(...)
    #     await context.publication.create_entity(entity, actor_id, "Description")
    
    context.log("Migration completed")
'''
        
        migrate_path = migration_folder / "migrate.py"
        with open(migrate_path, 'w', encoding='utf-8') as f:
            f.write(migrate_template)
        
        click.echo(f"  Created: {migrate_path.relative_to(migrations_path.parent)}")
        
        # Create README.md from template
        readme_template = f'''# Migration: {migration_name}

## Purpose

[TODO: Describe the purpose of this migration]

## Data Sources

[TODO: List the data sources used in this migration]

- Source 1: Description and URL
- Source 2: Description and URL

## Changes

[TODO: Describe what changes this migration makes to the database]

- Creates X entities of type Y
- Updates Z entities with new attributes
- Creates relationships between A and B

## Dependencies

[TODO: List any dependencies on other migrations or external data]

- Depends on migration: XXX-migration-name
- Requires external data: description

## Notes

[TODO: Add any additional notes about this migration]

- This migration is deterministic and can be safely re-run
- Expected execution time: X minutes
- Special considerations: ...
'''
        
        readme_path = migration_folder / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_template)
        
        click.echo(f"  Created: {readme_path.relative_to(migrations_path.parent)}")
        
        # Success message
        click.echo(f"\n✓ Migration folder created successfully!")
        click.echo(f"\nNext steps:")
        click.echo(f"  1. Edit {migrate_path.relative_to(migrations_path.parent)} to implement your migration logic")
        click.echo(f"  2. Update {readme_path.relative_to(migrations_path.parent)} with migration details")
        click.echo(f"  3. Add any data files (CSV, JSON, Excel) to the migration folder")
        click.echo(f"  4. Test your migration with: nes2 migrate run {migration_name} --dry-run")
        click.echo(f"  5. Run your migration with: nes2 migrate run {migration_name}")
        click.echo()
    
    # Run async function
    asyncio.run(do_create())
