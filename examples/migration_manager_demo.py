"""
Demo script for the Migration Manager.

This script demonstrates how to use the MigrationManager to:
- Discover migrations
- Check which migrations have been applied
- Determine which migrations are pending
"""

import asyncio
from pathlib import Path

from nes2.services.migration import MigrationManager


async def main():
    """Demonstrate Migration Manager functionality."""
    
    # Initialize the Migration Manager
    migrations_dir = Path("migrations")
    db_repo_path = Path("nes-db")
    
    manager = MigrationManager(migrations_dir, db_repo_path)
    
    print("=" * 70)
    print("Migration Manager Demo")
    print("=" * 70)
    print()
    
    # Discover all migrations
    print("1. Discovering migrations...")
    print("-" * 70)
    migrations = await manager.discover_migrations()
    
    if not migrations:
        print("No migrations found in migrations/ directory")
        print()
        print("To create a migration:")
        print("  1. Create a folder: migrations/NNN-descriptive-name/")
        print("  2. Add migrate.py with AUTHOR, DATE, DESCRIPTION metadata")
        print("  3. Add README.md with documentation")
        return
    
    print(f"Found {len(migrations)} migration(s):\n")
    for migration in migrations:
        print(f"  {migration.full_name}")
        if migration.author:
            print(f"    Author: {migration.author}")
        if migration.date:
            print(f"    Date: {migration.date.strftime('%Y-%m-%d')}")
        if migration.description:
            print(f"    Description: {migration.description}")
        print()
    
    # Check applied migrations
    print("2. Checking applied migrations...")
    print("-" * 70)
    applied = await manager.get_applied_migrations()
    
    if applied:
        print(f"Found {len(applied)} applied migration(s):\n")
        for migration_name in applied:
            print(f"  ✓ {migration_name}")
        print()
    else:
        print("No migrations have been applied yet.")
        print("(No migration commits found in Database Repository)")
        print()
    
    # Check pending migrations
    print("3. Checking pending migrations...")
    print("-" * 70)
    pending = await manager.get_pending_migrations()
    
    if pending:
        print(f"Found {len(pending)} pending migration(s):\n")
        for migration in pending:
            print(f"  ○ {migration.full_name}")
            if migration.description:
                print(f"    {migration.description}")
        print()
    else:
        print("No pending migrations. All migrations have been applied.")
        print()
    
    # Check specific migration
    if migrations:
        print("4. Checking specific migration status...")
        print("-" * 70)
        first_migration = migrations[0]
        is_applied = await manager.is_migration_applied(first_migration)
        
        status = "applied" if is_applied else "pending"
        symbol = "✓" if is_applied else "○"
        print(f"{symbol} {first_migration.full_name} is {status}")
        print()
    
    print("=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
