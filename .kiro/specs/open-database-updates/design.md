# Design Document

## Overview

The Open Database Updates feature introduces a migration-based system for managing data evolution in the Nepal Entity Service. This system enables community contributions through versioned migration folders that contain executable Python scripts and supporting data files. The design follows database migration patterns (similar to Flyway, Alembic, or Django migrations) but applies them to data changes rather than schema changes.

### Two-Repository Architecture

The system operates across two GitHub repositories:

1. **Service API Repository** (https://github.com/NewNepal-org/NepalEntityService)
   - Contains application code (Python packages, API, CLI)
   - Contains migration scripts in `migrations/` directory
   - Lightweight repository (~10MB)
   - Contributors submit PRs here with new migrations
   - Maintainers review and merge migration PRs here

2. **Database Repository** (https://github.com/NewNepal-org/NepalEntityService-database)
   - Contains actual entity/relationship JSON files (100k-1M files)
   - Managed as Git submodule at `nes-db/` in Service API Repository
   - Large repository (~1GB+)
   - Modified by migration execution (not by direct PRs)
   - Tracks migration history through Git commits

**Workflow**:
1. Contributor creates migration folder in Service API Repository
2. Contributor submits PR to Service API Repository
3. Maintainer reviews migration code and merges PR
4. Maintainer executes migration locally using `nes2 migrate run`
5. Migration modifies files in Database Repository (nes-db/ submodule)
6. Migration system commits changes to Database Repository with metadata
7. Migration system pushes commits to Database Repository remote
8. Migration system updates submodule reference in Service API Repository

**Design Rationale**:
- **Separation of Concerns**: Application code and data are managed independently
- **Performance**: Service API repo remains lightweight for fast clones
- **Scalability**: Database repo can grow to millions of files without affecting service development
- **Review Process**: Migration code is reviewed separately from data changes
- **Audit Trail**: Git history in Database repo provides complete data evolution history
- **Flexibility**: Database repo can use different Git strategies (shallow clones, sparse checkout) without affecting service repo

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         GitHub: NepalEntityService (Service API Repo)        │
│                                                              │
│  migrations/                                                 │
│  ├── 000-initial-locations/                                 │
│  │   ├── migrate.py                                         │
│  │   ├── README.md                                          │
│  │   └── locations.csv                                      │
│  ├── 001-political-parties/                                 │
│  │   ├── migrate.py                                         │
│  │   ├── README.md                                          │
│  │   └── parties.json                                       │
│  └── 002-update-names/                                      │
│      ├── migrate.py                                         │
│      └── README.md                                          │
│                                                              │
│  nes-db/ (Git Submodule) ──────────────────────────┐        │
└────────────────────────────────────────────────────┼────────┘
                              │                      │
                              ▼                      │
┌─────────────────────────────────────────────────────────────┐
│                    Migration System                          │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Migration Runner │  │ Migration Manager│                │
│  │ (Execution)      │  │ (Discovery)      │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Migration Context│  │ Git Integration  │                │
│  │ (API for scripts)│  │ (Commit/Push)    │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Publication Service                         │
│         (Entity/Relationship Creation & Updates)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         GitHub: nes-db (Database Repo - Submodule)           │
│                                                              │
│  v2/                                                         │
│  ├── entity/                                                 │
│  │   ├── person/ (100k+ files)                              │
│  │   ├── organization/ (10k+ files)                         │
│  │   └── location/ (1k+ files)                              │
│  ├── relationship/ (500k+ files)                            │
│  └── version/ (1M+ files)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface                             │
│  nes2 migrate list                                          │
│  nes2 migrate status                                        │
│  nes2 migrate run [migration_name]                         │
│  nes2 migrate validate [migration_name]                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Manager                           │
│  - Discover migrations in migrations/ directory             │
│  - Track applied migrations                                 │
│  - Determine pending migrations                             │
│  - Validate migration structure                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Runner                            │
│  - Load migration script                                    │
│  - Create migration context                                 │
│  - Execute migration                                        │
│  - Handle errors and logging                                │
│  - Update migration history                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Migration Context                           │
│  - API for migration scripts                                │
│  - Access to Publication Service                            │
│  - Access to Entity Database (read)                         │
│  - Helper functions (bulk import, etc.)                     │
│  - Migration folder path                                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Migration Manager

**Responsibility**: Discover and validate migrations.

**Key Methods**:
```python
class MigrationManager:
    def __init__(self, migrations_dir: Path):
        """Initialize with migrations directory."""
        
    async def discover_migrations(self) -> List[Migration]:
        """Scan migrations directory and return sorted list of migrations."""
        
    async def validate_migration(self, migration: Migration) -> ValidationResult:
        """Validate migration structure and script syntax."""
        
    def get_migration_by_name(self, name: str) -> Optional[Migration]:
        """Get a specific migration by its full name."""
```

### 2. Migration Runner

**Responsibility**: Execute migration scripts and manage Git operations.

**Key Methods**:
```python
class MigrationRunner:
    def __init__(
        self, 
        publication_service: PublicationService,
        db: EntityDatabase,
        db_repo_path: Path
    ):
        """Initialize with services and database repo path."""
        
    async def run_migration(
        self, 
        migration: Migration,
        dry_run: bool = False,
        auto_commit: bool = True,
        force: bool = False
    ) -> MigrationResult:
        """
        Execute a migration script and optionally commit changes.
        
        Args:
            migration: Migration to execute
            dry_run: If True, don't commit changes
            auto_commit: If True, commit and push changes after execution
            force: If True, allow re-execution of already-applied migrations
        
        Returns:
            MigrationResult with execution details
            
        Raises:
            MigrationAlreadyAppliedException: If migration was already applied and force=False
        """
        
    async def run_migrations(
        self,
        migrations: List[Migration],
        dry_run: bool = False,
        auto_commit: bool = True
    ) -> List[MigrationResult]:
        """Execute multiple migrations in order, skipping already-applied ones."""
        
    def create_context(self, migration: Migration) -> MigrationContext:
        """Create execution context for migration script."""
        
    async def commit_and_push(
        self,
        migration: Migration,
        result: MigrationResult
    ) -> None:
        """
        Commit database changes and push to remote.
        
        This persists the data snapshot in the Database Repository,
        making the migration deterministic on subsequent runs.
        """
    
    async def is_migration_applied(self, migration: Migration) -> bool:
        """Check if migration has already been applied by checking persisted snapshots."""
```

**Design Decision**: The Migration Runner checks persisted snapshots before executing migrations to prevent re-execution. Once a migration is committed to the Database Repository, the data snapshot is persisted and the migration is considered applied. This ensures:
- **Determinism**: Re-running a migration produces the same result (no-op if already applied)
- **Idempotency**: Safe to run `nes2 migrate run --all` multiple times
- **Data Integrity**: Prevents duplicate entities from accidental re-execution
- **Audit Trail**: Git history serves as the source of truth for applied migrations

### 3. Migration Context

**Responsibility**: Provide minimal context and utilities for migration scripts.

**Key Methods**:
```python
class MigrationContext:
    """Thin context object passed to migration scripts."""
    
    def __init__(
        self,
        publication_service: PublicationService,
        search_service: SearchService,
        scraping_service: ScrapingService,
        db: EntityDatabase,
        migration_dir: Path
    ):
        """Initialize with services and migration directory."""
        self.publication = publication_service
        self.search = search_service
        self.scraping = scraping_service
        self.db = db
        self._migration_dir = migration_dir
        self._logs = []
    
    @property
    def migration_dir(self) -> Path:
        """Path to the migration folder."""
        return self._migration_dir
    
    # File reading helpers
    def read_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Read CSV file from migration folder."""
        file_path = self._migration_dir / filename
        # Implementation with CSV reader
        
    def read_json(self, filename: str) -> Any:
        """Read JSON file from migration folder."""
        file_path = self._migration_dir / filename
        # Implementation with JSON reader
        
    def read_excel(
        self,
        filename: str,
        sheet_name: str = None
    ) -> List[Dict[str, Any]]:
        """Read Excel file from migration folder."""
        file_path = self._migration_dir / filename
        # Implementation with Excel reader
    
    # Logging
    def log(self, message: str) -> None:
        """Log a message during migration execution."""
        self._logs.append(message)
        print(f"[Migration] {message}")
```

**Migration Script Usage**:
```python
async def migrate(context):
    """Migration scripts use services directly."""
    # Read data
    ministers = context.read_csv("ministers.csv")
    
    # Use publication service directly
    actor_id = "actor:migration:005-add-ministers"
    
    for row in ministers:
        entity = Entity(...)
        
        # Direct service call (no wrapper)
        await context.publication.create_entity(
            entity=entity,
            actor_id=actor_id,
            change_description="Import minister"
        )
    
    # Use search service directly
    existing = await context.search.find_entity_by_name("Ram Sharma")
    
    # Use scraping service directly
    normalized = await context.scraping.normalize_name("राम शर्मा")
    
    context.log(f"Imported {len(ministers)} ministers")
```

**Design Decision**: The MigrationContext is intentionally thin, providing only:
- **Service Access**: Direct access to publication, search, and scraping services (no wrappers)
- **File Helpers**: Convenience methods for reading CSV/JSON/Excel from migration folder
- **Logging**: Simple logging mechanism for migration progress
- **No Statistics Tracking**: Migration runner tracks statistics by monitoring service calls
- **No Validation**: Services handle their own validation
- **Minimal API**: Reduces maintenance burden and keeps migrations simple

### 4. Migration Models

**Data Models**:
```python
@dataclass
class Migration:
    """Represents a migration folder."""
    prefix: int  # Numeric prefix (000, 001, etc.)
    name: str  # Descriptive name
    folder_path: Path  # Full path to migration folder
    script_path: Path  # Path to migrate.py or run.py
    readme_path: Optional[Path]  # Path to README.md if exists
    author: Optional[str]  # Author from migration metadata
    date: Optional[datetime]  # Date from migration metadata
    
    @property
    def full_name(self) -> str:
        """Returns formatted name like '000-initial-locations'."""
        return f"{self.prefix:03d}-{self.name}"
    
@dataclass
class MigrationResult:
    """Result of migration execution."""
    migration: Migration
    status: MigrationStatus
    duration_seconds: float
    entities_created: int
    entities_updated: int
    relationships_created: int
    error: Optional[Exception]
    logs: List[str]
    git_commit_sha: Optional[str]  # SHA of commit in database repo

class MigrationStatus(str, Enum):
    """Status of a migration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Data Models

### Two-Repository Architecture

**Service API Repository** (NepalEntityService):
```
NepalEntityService/
├── migrations/
│   ├── 000-initial-locations/
│   ├── 001-political-parties/
│   └── 002-update-names/
├── nes2/
│   ├── services/
│   │   └── migration/  (new)
│   └── ...
├── nes-db/  (Git submodule pointing to Database repo)
└── ...
```

**Database Repository** (nes-db):
```
nes-db/
├── v2/
│   ├── entity/
│   │   ├── person/
│   │   │   ├── ram-chandra-poudel.json
│   │   │   ├── sher-bahadur-deuba.json
│   │   │   └── ... (100k+ files)
│   │   ├── organization/
│   │   │   └── ... (10k+ files)
│   │   └── location/
│   │       └── ... (1k+ files)
│   ├── relationship/
│   │   └── ... (500k+ files)
│   ├── version/
│   │   └── ... (1M+ files)
│   └── actor/
│       └── ... (1k+ files)
└── README.md
```

### Migration History via Git

Instead of maintaining a separate migration history table, we rely on Git history in the Database Repository:

**Git Commit Message Format**:
```
Migration: 000-initial-locations

Imported initial location data for Nepal's administrative divisions.

Author: contributor@example.com
Date: 2024-01-20
Entities created: 753
Relationships created: 0
Duration: 45.2s
```

**Benefits**:
- Git provides complete audit trail
- No need for separate tracking system
- Can use `git log` to see migration history
- Can use `git revert` to rollback migrations
- Distributed version control for database

**Determining Applied Migrations**:

The Migration Manager determines which migrations have been applied by checking persisted snapshots in the Database Repository. This ensures that once a migration's data snapshot is persisted, the system knows not to re-execute it:

```python
class MigrationManager:
    def __init__(self, migrations_dir: Path, db_repo_path: Path):
        self.migrations_dir = migrations_dir
        self.db_repo_path = db_repo_path
        self._applied_cache = None  # Cache to avoid repeated Git queries
    
    async def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migration names by checking persisted snapshots.
        
        This queries the Database Repository's Git log to find all commits
        that represent persisted data snapshots from applied migrations.
        Each commit serves as proof that the migration was executed.
        """
        if self._applied_cache is not None:
            return self._applied_cache
        
        # Query git log in database repo for migration commits (persisted snapshots)
        result = subprocess.run(
            ["git", "log", "--grep=^Migration:", "--format=%s"],
            cwd=self.db_repo_path,
            capture_output=True,
            text=True
        )
        
        # Parse migration names from commit messages
        applied = []
        for line in result.stdout.split('\n'):
            if line.startswith('Migration: '):
                migration_name = line.replace('Migration: ', '').strip()
                # Remove batch suffix if present (e.g., "000-test (Batch 1/3)" -> "000-test")
                if ' (Batch ' in migration_name:
                    migration_name = migration_name.split(' (Batch ')[0]
                if migration_name not in applied:
                    applied.append(migration_name)
        
        self._applied_cache = applied
        return applied
    
    async def get_pending_migrations(self) -> List[Migration]:
        """
        Get migrations that haven't been applied yet.
        
        Returns only migrations whose data snapshots have not been
        persisted in the Database Repository.
        """
        all_migrations = await self.discover_migrations()
        applied = await self.get_applied_migrations()
        
        pending = []
        for migration in all_migrations:
            if migration.full_name not in applied:
                pending.append(migration)
        
        return pending
    
    async def is_migration_applied(self, migration: Migration) -> bool:
        """Check if a specific migration has been applied."""
        applied = await self.get_applied_migrations()
        return migration.full_name in applied
```

**Querying Migration History**:
```bash
# See all migrations applied (in Database Repository)
cd nes-db/
git log --grep="Migration:" --oneline

# See details of a specific migration
git show <commit-sha>

# See what changed in a migration
git diff <commit-sha>~1 <commit-sha>

# Revert a migration
git revert <commit-sha>
```

**Design Decision**: Using persisted snapshots as the source of truth for applied migrations eliminates the need for a separate tracking database. When a migration is executed, the resulting data snapshot is committed to the Database Repository, which serves as both:
1. **Persistence**: The actual entity/relationship data is stored
2. **Tracking**: The persisted snapshot proves the migration was applied

This approach:
- **Ensures Determinism**: Re-running a migration is a no-op since the system detects the persisted snapshot
- **Leverages Git**: Uses Git commits to store snapshots instead of a separate tracking system
- **Maintains Sync**: Migration history is always in sync with actual database state (they're the same thing)
- **Enables Distribution**: Multiple maintainers can see the same snapshots by pulling from the Database Repository
- **Provides Rollback**: Standard Git operations (revert, reset) can undo migrations by reverting snapshots
- **Prevents Duplicates**: Accidental re-execution is blocked by checking for existing snapshots

### Migration Folder Structure

**Standard Structure**:
```
migrations/
├── 000-initial-locations/
│   ├── migrate.py          # Main migration script (required)
│   ├── README.md           # Documentation (required)
│   ├── locations.csv       # Data file (optional)
│   └── sources.txt         # Source references (optional)
├── 001-political-parties/
│   ├── migrate.py
│   ├── README.md
│   ├── parties.json
│   └── logos/              # Subdirectory for assets (optional)
│       ├── party1.png
│       └── party2.png
└── 002-update-names/
    ├── migrate.py
    ├── README.md
    └── corrections.xlsx
```

**Migration Script Template** (migrate.py):

The `nes2 migrate create <name>` command generates a migration folder from this template:

```python
"""
Migration: {prefix}-{name}
Description: [TODO: Describe what this migration does]
Author: [TODO: Your email]
Date: {current_date}
"""

# Migration metadata (used for Git commit message)
AUTHOR = "[TODO: Your email]"
DATE = "{current_date}"
DESCRIPTION = "[TODO: Describe what this migration does]"

async def migrate(context):
    """
    Main migration function.
    
    Args:
        context: MigrationContext with access to services and data
        
    Available context methods:
        - context.create_entity(entity, actor_id, change_description)
        - context.update_entity(entity_id, updates, actor_id, change_description)
        - context.create_relationship(relationship, actor_id, change_description)
        - context.get_entity(entity_id)
        - context.search_entities(query, **filters)
        - context.find_entity_by_name(name, entity_type)
        - context.normalize_name(raw_name, language)
        - context.read_csv(filename)
        - context.read_json(filename)
        - context.read_excel(filename, sheet_name)
        - context.log(message)
    """
    # TODO: Implement your migration logic here
    
    # Example: Read data from CSV
    # data = context.read_csv("data.csv")
    
    # Example: Create actor for this migration
    # actor_id = "actor:migration:{prefix}-{name}"
    
    # Example: Process each row
    # for row in data:
    #     entity = Entity(...)
    #     await context.create_entity(entity, actor_id, "Description")
    
    context.log("Migration completed")
```

**Example Migration** (000-initial-locations/migrate.py):
```python
"""
Migration: 000-initial-locations
Description: Import initial location data from administrative divisions CSV
Author: contributor@example.com
Date: 2024-01-20
"""

# Migration metadata (used for Git commit message)
AUTHOR = "contributor@example.com"
DATE = "2024-01-20"
DESCRIPTION = "Import initial location data from administrative divisions CSV"

async def migrate(context):
    """
    Main migration function.
    
    Args:
        context: MigrationContext with access to services and data
    """
    # Read data from CSV
    locations = context.read_csv("locations.csv")
    
    # Create actor for this migration
    actor_id = "actor:migration:000-initial-locations"
    
    # Process each location
    for loc_data in locations:
        entity = Entity(
            slug=loc_data["slug"],
            type=EntityType.LOCATION,
            sub_type=loc_data["sub_type"],
            names=[
                Name(
                    kind=NameKind.PRIMARY,
                    en=NameParts(full=loc_data["name_en"]),
                    ne=NameParts(full=loc_data["name_ne"])
                )
            ],
            attributes={"code": loc_data["code"]}
        )
        
        await context.create_entity(
            entity=entity,
            actor_id=actor_id,
            change_description=f"Initial import of {loc_data['name_en']}"
        )
    
    context.log(f"Imported {len(locations)} locations")
```

**Design Decision**: The `nes2 migrate create` command provides a standardized template that:
- Automatically assigns the next available prefix number
- Pre-fills the current date
- Includes comprehensive documentation of available context methods
- Provides example code patterns for common operations
- Ensures consistent structure across all migrations
- Lowers the barrier for new contributors

**README.md Template**:
```markdown
# Migration: 000-initial-locations

## Purpose
Import initial location data for Nepal's administrative divisions including provinces, districts, and municipalities.

## Data Sources
- Nepal Government Open Data Portal: https://data.gov.np/...
- Administrative divisions CSV from 2023 census

## Changes
- Creates 753 location entities (7 provinces, 77 districts, 669 municipalities)
- Includes both Nepali and English names
- Includes official administrative codes

## Dependencies
None (initial migration)

## Notes
This is a deterministic migration that will produce identical results on each run.
```

## Git Workflow

### Migration Execution and Commit Flow

**Step-by-Step Process**:

1. **Contributor submits migration PR** to Service API repo
   ```bash
   # In NepalEntityService repo
   git checkout -b add-migration-003
   # Create migration folder with script and data
   git add migrations/003-new-entities/
   git commit -m "Add migration: 003-new-entities"
   git push origin add-migration-003
   # Create PR on GitHub
   ```

2. **Maintainer reviews and merges PR** to Service API repo
   ```bash
   # Maintainer reviews code, validates migration
   # Merges PR on GitHub
   ```

3. **Maintainer executes migration** locally
   ```bash
   # Pull latest migrations
   git pull origin main
   
   # Run migration (modifies files in nes-db/ submodule)
   nes2 migrate run 003-new-entities
   
   # Migration system automatically:
   # 1. Checks if migration already applied (looks for persisted snapshot in nes-db/)
   # 2. If snapshot exists, skips execution (ensures determinism)
   # 3. If no snapshot, executes migration script
   # 4. Creates/updates files in nes-db/v2/
   # 5. Commits changes to nes-db submodule (persists data snapshot)
   # 6. Pushes to nes-db remote (makes snapshot available to others)
   # 7. Updates submodule reference in Service API repo
   ```
   
   **Key Point**: Once step 5 (commit) completes, the data snapshot is persisted in the Database Repository. This makes the migration deterministic—running it again will detect the existing persisted snapshot and skip execution.

4. **Database repo updated** with new entities
   ```bash
   # In nes-db repo, new commit appears:
   # Commit: abc123
   # Message: Migration: 003-new-entities
   #          
   #          Added 50 new political entities
   #          
   #          Author: contributor@example.com
   #          Date: 2024-01-22
   #          Entities created: 50
   #          Duration: 12.3s
   ```

### Handling Large Database Repository (100k-1M files)

**Challenges**:
- Git performance degrades with very large number of files
- Clone times become prohibitive
- Disk space requirements increase

**Solutions**:

**1. Git LFS (Large File Storage)** - NOT RECOMMENDED
- Git LFS is for large binary files, not many small files
- Would not help with our use case

**2. Shallow Clones**
```bash
# Clone with limited history
git clone --depth 1 https://github.com/org/nes-db.git

# Fetch only recent history when needed
git fetch --depth 10
```

**3. Sparse Checkout** (Recommended for development)
```bash
# Clone only specific directories
git clone --filter=blob:none --sparse https://github.com/org/nes-db.git
cd nes-db
git sparse-checkout set v2/entity/person v2/entity/organization
```

**4. Git Worktrees** (For parallel operations)
```bash
# Create separate worktrees for different entity types
git worktree add ../nes-db-persons v2/entity/person
git worktree add ../nes-db-orgs v2/entity/organization
```

**5. Batch Commits** (Recommended for migrations)

When migrations create or modify large numbers of files (e.g., 10,000+ entities), committing all changes in a single Git commit can cause performance issues. The Migration Runner implements batch commits:

```python
class MigrationRunner:
    BATCH_COMMIT_THRESHOLD = 1000  # Commit in batches if more than 1000 files changed
    BATCH_SIZE = 1000  # Files per batch commit
    
    async def commit_and_push(
        self,
        migration: Migration,
        result: MigrationResult,
        auto_commit: bool = True
    ) -> None:
        """Commit changes in batches to avoid huge commits."""
        if not auto_commit:
            return
        
        # Get list of changed files
        changed_files = self._get_changed_files()
        
        if len(changed_files) == 0:
            self.log("No changes to commit")
            return
        
        # If below threshold, commit all at once
        if len(changed_files) < self.BATCH_COMMIT_THRESHOLD:
            self._commit_all(migration, result, changed_files)
            self._push()
            return
        
        # Otherwise, commit in batches
        self.log(f"Committing {len(changed_files)} files in batches of {self.BATCH_SIZE}")
        
        for i in range(0, len(changed_files), self.BATCH_SIZE):
            batch = changed_files[i:i+self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            total_batches = (len(changed_files) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            
            # Stage batch
            subprocess.run(
                ["git", "add"] + batch,
                cwd=self.db_repo_path,
                check=True
            )
            
            # Commit batch with metadata
            commit_msg = self._format_batch_commit_message(
                migration, result, batch_num, total_batches
            )
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.db_repo_path,
                check=True
            )
            
            self.log(f"Committed batch {batch_num}/{total_batches}")
        
        # Push all commits at once
        self.log("Pushing commits to remote...")
        subprocess.run(
            ["git", "push"],
            cwd=self.db_repo_path,
            check=True,
            timeout=300  # 5 minute timeout for large pushes
        )
        
        self.log("All changes committed and pushed")
    
    def _format_batch_commit_message(
        self,
        migration: Migration,
        result: MigrationResult,
        batch_num: int,
        total_batches: int
    ) -> str:
        """Format commit message for batch commit."""
        return f"""Migration: {migration.full_name} (Batch {batch_num}/{total_batches})

{migration.DESCRIPTION}

Author: {migration.AUTHOR}
Date: {migration.DATE}
Batch: {batch_num} of {total_batches}
"""
```

**Design Decision**: Batch commits are automatically triggered when a migration modifies more than 1000 files. This approach:
- Keeps individual commits manageable in size
- Prevents Git performance degradation
- Maintains atomic batches that can be reverted if needed
- Provides progress feedback during long commit operations
- Uses a single push operation to minimize network overhead
- Includes batch metadata in commit messages for traceability

**6. Git Configuration for Large Repos**
```bash
# Increase Git performance for large repos
git config core.preloadindex true
git config core.fscache true
git config gc.auto 256
git config pack.threads 4
```

**7. Alternative: Git Annex** (Future consideration)
- Designed for managing large numbers of files
- Keeps file metadata in Git, content elsewhere
- More complex but better for very large repos

### Rollback Strategy

**Using Git Revert**:
```bash
# Revert a migration by reverting its commit
git revert <migration-commit-sha>

# This creates a new commit that undoes the changes
# Preserves history and is safe for shared repos
```

**Manual Rollback**:
```bash
# If git revert is not sufficient, create a rollback migration
nes2 migrate create 010-rollback-009

# In 010-rollback-009/migrate.py:
# - Delete entities created by migration 009
# - Restore previous state
# - Document why rollback was needed
```

**Best Practices**:
- Always test migrations in a separate branch first
- Use dry-run mode before actual execution
- Keep migrations small and focused
- Document rollback procedures in README.md

## Error Handling

### Migration Execution Errors

**Error Categories**:
1. **Syntax Errors**: Python syntax errors in migration script
2. **Validation Errors**: Entity data doesn't conform to schema
3. **Referential Integrity Errors**: References to non-existent entities
4. **File Not Found Errors**: Missing data files referenced in script
5. **GenAI API Errors**: Failures in AI service calls
6. **Database Errors**: Failures writing to Entity Database

**Error Handling Strategy**:
```python
async def run_migration(self, migration: Migration) -> MigrationResult:
    """Execute migration with comprehensive error handling."""
    start_time = time.time()
    result = MigrationResult(migration=migration)
    
    try:
        # Load and validate script
        script = self._load_script(migration.script_path)
        
        # Create context
        context = self.create_context(migration)
        
        # Execute migration
        await script.migrate(context)
        
        result.status = MigrationStatus.COMPLETED
        result.entities_created = context.entities_created
        result.entities_updated = context.entities_updated
        
    except SyntaxError as e:
        result.status = MigrationStatus.FAILED
        result.error = e
        result.logs.append(f"Syntax error: {e}")
        
    except ValidationError as e:
        result.status = MigrationStatus.FAILED
        result.error = e
        result.logs.append(f"Validation error: {e}")
        
    except Exception as e:
        result.status = MigrationStatus.FAILED
        result.error = e
        result.logs.append(f"Unexpected error: {e}")
        
    finally:
        result.duration_seconds = time.time() - start_time
        
    return result
```

### Service Integration Error Handling

**Service Failures**: Migration scripts may encounter errors when calling Publication, Search, or Scraping services:

```python
class MigrationContext:
    async def create_entity(
        self,
        entity: Entity,
        actor_id: str,
        change_description: str
    ) -> Entity:
        """Create entity with error handling."""
        try:
            result = await self.publication_service.create_entity(
                entity=entity,
                actor_id=actor_id,
                change_description=change_description
            )
            self.entities_created += 1
            return result
        except ValidationError as e:
            # Log validation error with entity details
            self.log(f"Validation error for entity {entity.slug}: {e}")
            raise
        except Exception as e:
            # Log unexpected error
            self.log(f"Failed to create entity {entity.slug}: {e}")
            raise
    
    async def normalize_name(
        self,
        raw_name: str,
        language: str = "nepali"
    ) -> Dict[str, Any]:
        """Normalize name with error handling."""
        try:
            return await self.scraping_service.normalize_name(
                raw_name=raw_name,
                language=language
            )
        except Exception as e:
            # Log error but allow migration to continue with fallback
            self.log(f"Name normalization failed for '{raw_name}': {e}")
            # Return fallback result
            return {
                "slug": raw_name.lower().replace(" ", "-"),
                "nepali": raw_name,
                "english": raw_name,
                "confidence": 0.0
            }
```

**Design Decision**: Service errors are logged and propagated to the migration script, which can decide whether to:
- Fail the entire migration (default behavior)
- Continue with fallback values (for non-critical operations like name normalization)
- Skip problematic records and continue processing others

### Recovery from Failed Migrations

**Approach**: No automatic rollback. Failed migrations require manual intervention.

**Rationale**:
- Data migrations are complex and automatic rollback could cause data loss
- Git history provides complete audit trail
- Maintainers can use git revert or write corrective migrations
- Manual review ensures proper handling of failures

**Recovery Process**:
1. Migration fails during execution
2. System logs error details with full stack trace
3. No commit is made to Database Repository (changes not persisted)
4. Maintainer investigates error logs
5. Maintainer either:
   - Fixes the migration script and retries
   - Writes a corrective migration to undo partial changes
   - Uses git to discard uncommitted changes in Database Repository

## Testing Strategy

### Unit Tests

**Test Coverage**:
1. **Migration Discovery**: Test finding and sorting migrations
2. **Migration Validation**: Test validation of folder structure and scripts
3. **Migration History**: Test tracking applied migrations
4. **Context API**: Test all MigrationContext methods
5. **Error Handling**: Test various error scenarios

**Example Test**:
```python
async def test_migration_discovery():
    """Test that migrations are discovered and sorted correctly."""
    manager = MigrationManager(migrations_dir=test_migrations_path, db=mock_db)
    
    migrations = await manager.discover_migrations()
    
    assert len(migrations) == 3
    assert migrations[0].prefix == 0
    assert migrations[0].name == "initial-locations"
    assert migrations[1].prefix == 1
    assert migrations[2].prefix == 2
```

### Integration Tests

**Test Scenarios**:
1. **End-to-End Migration**: Run a complete migration and verify entities created
2. **Migration with CSV**: Test reading CSV files and creating entities
3. **Migration with Relationships**: Test creating entities and relationships
4. **Failed Migration**: Test error handling and history recording
5. **Idempotent Migration**: Test running same migration twice

**Example Test**:
```python
async def test_migration_creates_entities(test_db, publication_service):
    """Test that migration successfully creates entities."""
    # Setup
    runner = MigrationRunner(publication_service, test_db)
    migration = Migration(
        prefix=0,
        name="test-migration",
        folder_path=test_migration_path,
        script_path=test_migration_path / "migrate.py"
    )
    
    # Execute
    result = await runner.run_migration(migration)
    
    # Verify
    assert result.status == MigrationStatus.COMPLETED
    assert result.entities_created == 5
    
    # Check entities exist in database
    entities = await test_db.list_entities()
    assert len(entities) == 5
```

### Manual Testing

**Test Checklist**:
- [ ] Create a new migration folder with CSV data
- [ ] Run `nes2 migrate list` to see pending migration
- [ ] Run `nes2 migrate validate 000-test` to validate
- [ ] Run `nes2 migrate run 000-test` to execute
- [ ] Verify entities created in database
- [ ] Check migration history recorded
- [ ] Test error handling with invalid migration
- [ ] Test dry-run mode

## CLI Commands

### Command Structure

```bash
# List all migrations and their status (applied/pending)
nes2 migrate list

# Show migration history (applied migrations from Git log)
nes2 migrate history

# Show pending migrations (not yet applied)
nes2 migrate pending

# Validate a specific migration
nes2 migrate validate <migration_name>

# Validate all pending migrations
nes2 migrate validate --all

# Run a specific migration
nes2 migrate run <migration_name>

# Run all pending migrations
nes2 migrate run --all

# Run migration in dry-run mode (no changes applied)
nes2 migrate run <migration_name> --dry-run

# Create a new migration folder from template
nes2 migrate create <descriptive-name>
```

**Command Implementation Details**:

**`nes2 migrate list`**: 
- Discovers all migrations in migrations/ directory
- Queries Git history in Database Repository to determine which are applied
- Shows each migration with status (✓ Applied / ○ Pending)
- Displays metadata (author, date, description) from migration script

**`nes2 migrate history`**:
- Queries Git log in Database Repository for migration commits
- Parses commit messages to extract migration metadata
- Shows applied migrations in chronological order with statistics

**`nes2 migrate pending`**:
- Discovers all migrations in migrations/ directory
- Queries Git history to find applied migrations
- Returns only migrations not yet applied
- Useful for seeing what will run with `nes2 migrate run --all`

**`nes2 migrate create <name>`**:
- Creates a new migration folder with next available prefix
- Copies template files (migrate.py, README.md) into folder
- Pre-fills metadata with current date and prompts for author
- Provides starting point for contributors

### Command Output Examples

**`nes2 migrate list`**:
```
Migrations:
  ✓ 000-initial-locations (Applied)
    Author: contributor@example.com
    Date: 2024-01-20
    Description: Import initial location data
    
  ✓ 001-political-parties (Applied)
    Author: contributor@example.com
    Date: 2024-01-21
    Description: Import political party entities
    
  ○ 002-update-names (Pending)
    Author: contributor2@example.com
    Date: 2024-01-22
    Description: Update entity names with corrections
    
  ○ 003-add-relationships (Pending)
    Author: contributor@example.com
    Date: 2024-01-23
    Description: Add membership relationships

Total: 4 migrations (2 applied, 2 pending)
```

**`nes2 migrate history`**:
```
Applied Migrations (from Git history):

000-initial-locations
  Applied: 2024-01-20 10:30:00
  Author: contributor@example.com
  Entities created: 753
  Duration: 45.2s
  Commit: abc123def

001-political-parties
  Applied: 2024-01-21 14:15:00
  Author: contributor@example.com
  Entities created: 12
  Duration: 3.1s
  Commit: def456ghi

Total: 2 migrations applied
```

**`nes2 migrate pending`**:
```
Pending Migrations:

002-update-names
  Author: contributor2@example.com
  Date: 2024-01-22
  Description: Update entity names with corrections

003-add-relationships
  Author: contributor@example.com
  Date: 2024-01-23
  Description: Add membership relationships

Total: 2 pending migrations
```

**`nes2 migrate run 002-update-names`**:
```
Running migration: 002-update-names
Reading corrections.xlsx...
Updating 45 entity names...
  ✓ Updated entity:person/ram-chandra-poudel
  ✓ Updated entity:person/sher-bahadur-deuba
  ...
  
Migration completed successfully!
  Duration: 8.3 seconds
  Entities updated: 45
  
Committing changes to database repository...
  ✓ Committed to nes-db (commit: xyz789abc)
  ✓ Pushed to remote

Migration applied and persisted.
```

**`nes2 migrate run 002-update-names` (already applied)**:
```
Migration 002-update-names has already been applied.
Applied on: 2024-01-22 15:30:00
Commit: xyz789abc

Skipping execution. Use --force to re-run.
```

## Integration with Existing System

### Publication Service Integration

The Migration System will use the existing Publication Service for all entity and relationship operations:

```python
class MigrationContext:
    def __init__(self, publication_service: PublicationService, ...):
        self.publication_service = publication_service
        
    async def create_entity(self, entity: Entity, actor_id: str, change_description: str):
        """Delegate to Publication Service."""
        return await self.publication_service.create_entity(
            entity=entity,
            actor_id=actor_id,
            change_description=change_description
        )
```

**Benefits**:
- All validation rules enforced
- Automatic versioning
- Consistent actor attribution
- Referential integrity maintained

### Actor Attribution

Migrations will create special actor records:

```python
actor = Actor(
    id="actor:migration:000-initial-locations",
    type="migration",
    name="Migration: 000-initial-locations",
    metadata={
        "migration_name": "000-initial-locations",
        "contributor": "contributor@example.com",
        "executed_by": "maintainer@example.com",
        "executed_at": "2024-01-20T10:30:00Z"
    }
)
```

This ensures full traceability from entity version back to the migration that created it.

## Linear Migration Model

### Sequential Execution

**Design Principle**: Migrations are applied in strict sequential order with no forking or merging.

**Characteristics**:

1. **Numeric Prefixes**: Migrations numbered sequentially (000, 001, 002, ...)
2. **Single Branch**: All migrations applied to main branch only
3. **No Parallel Execution**: One migration at a time
4. **No Rollback**: Migrations are forward-only; corrections done via new migrations
5. **Deterministic Order**: Same sequence on all environments

**Migration Sequence**:
```
000-initial-locations  →  001-political-parties  →  002-update-names  →  003-add-ministers
     (applied)                 (applied)                (applied)            (pending)
```

**Conflict Prevention**:
- Contributors must pull latest migrations before creating new ones
- Next available prefix assigned automatically by `nes2 migrate create`
- PR review ensures no duplicate prefixes
- Automated service processes migrations in order

**Correction Strategy**:
If a migration introduces errors, create a new corrective migration:
```
005-add-incorrect-data  →  006-correct-data-from-005
     (applied)                    (new migration)
```

**Design Rationale**: Linear migrations provide:
- **Simplicity**: Easy to understand and reason about
- **Predictability**: Same sequence everywhere
- **No Conflicts**: No merge conflicts in data
- **Clear History**: Straightforward audit trail
- **No Rollback Complexity**: Forward-only is simpler and safer

## Migration Determinism and Idempotency

### Determinism Through Persisted Snapshots

**Problem**: Migration scripts may contain non-deterministic operations (e.g., GenAI calls, timestamps, random IDs). Running the same migration twice could create duplicate entities or inconsistent data.

**Solution**: The Migration System ensures determinism by persisting the data snapshot after each migration execution and preventing re-execution:

```python
async def run_migration(
    self,
    migration: Migration,
    dry_run: bool = False,
    auto_commit: bool = True,
    force: bool = False
) -> MigrationResult:
    """Execute migration with determinism guarantee."""
    
    # Check if migration already applied
    if not force and await self.is_migration_applied(migration):
        return MigrationResult(
            migration=migration,
            status=MigrationStatus.SKIPPED,
            message="Migration already applied"
        )
    
    # Execute migration
    result = await self._execute_migration(migration)
    
    # Persist data snapshot (commit to Database Repository)
    if not dry_run and auto_commit and result.status == MigrationStatus.COMPLETED:
        await self.commit_and_push(migration, result)
        # Now migration is marked as applied in Git history
    
    return result
```

**Guarantees**:

1. **Single Execution**: Each migration executes at most once (unless forced)
2. **Persisted State**: The resulting data snapshot is committed to Git
3. **Idempotent Commands**: Running `nes2 migrate run --all` multiple times is safe
4. **No Duplicates**: Entities created by a migration won't be duplicated on re-run
5. **Consistent Results**: The data snapshot in Git represents the canonical result

**Example Scenario**:

```bash
# First execution
$ nes2 migrate run 003-add-entities
Running migration: 003-add-entities
Created 100 entities
Committed to nes-db (commit: abc123)
✓ Migration applied

# Second execution (deterministic - no-op)
$ nes2 migrate run 003-add-entities
Migration 003-add-entities has already been applied.
Skipping execution.

# Force re-execution (if needed for testing)
$ nes2 migrate run 003-add-entities --force
Warning: Re-executing already-applied migration
Running migration: 003-add-entities
Created 100 entities (duplicates!)
```

**Design Decision**: By persisting the data snapshot in Git and checking for persisted snapshots before execution, the system guarantees that migrations are deterministic from the user's perspective. Even if the migration script itself contains non-deterministic logic (GenAI, timestamps), it only runs once, and the persisted snapshot becomes the canonical result. This prevents data corruption from accidental re-execution while still allowing forced re-runs for testing or recovery scenarios.

## GenAI Integration

### Configuration

GenAI providers will be configured via environment variables:

```bash
# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=...
GOOGLE_APPLICATION_CREDENTIALS=...

# OpenAI
OPENAI_API_KEY=...
```

### Usage in Migrations

```python
async def migrate(context):
    """Migration using GenAI for name normalization."""
    
    # Get GenAI client from context
    genai = context.get_genai_client(provider="openai")
    
    # Read raw data
    raw_names = context.read_csv("raw_names.csv")
    
    for raw in raw_names:
        # Use GenAI to normalize name
        normalized = await genai.normalize_name(
            raw_name=raw["name"],
            language="nepali"
        )
        
        # Create entity with normalized name
        entity = Entity(
            slug=normalized["slug"],
            type=EntityType.PERSON,
            names=[
                Name(
                    kind=NameKind.PRIMARY,
                    ne=NameParts(full=normalized["nepali"]),
                    en=NameParts(full=normalized["english"])
                )
            ]
        )
        
        await context.create_entity(
            entity=entity,
            actor_id="actor:migration:003-normalize-names",
            change_description=f"Normalized name using GenAI: {raw['name']}"
        )
```

### Non-Deterministic Handling

Migrations using GenAI will be marked as non-deterministic:

```python
# In migrate.py
DETERMINISTIC = False  # Flag indicating non-deterministic migration

async def migrate(context):
    """Non-deterministic migration using GenAI."""
    # ... GenAI operations ...
```

The Migration System will:
- Record the GenAI provider and model used
- Log confidence scores from GenAI outputs
- Mark the migration as non-deterministic in history
- Warn users that re-running may produce different results

## Security Considerations

### GitHub PR Review

**Security Measures**:
1. All migrations must be submitted via GitHub pull requests
2. Maintainers review migration code before merging
3. Automated checks validate migration structure and syntax
4. No direct execution of untrusted code

### Migration Execution

**Security Measures**:
1. Migrations run in the same process as the application (no sandboxing needed since code is reviewed)
2. All database operations go through Publication Service (validation enforced)
3. Migration history tracks who executed each migration
4. Failed migrations are logged for audit

### Data Access

**Security Measures**:
1. Migration scripts have read access to Entity Database
2. Write operations only through Publication Service
3. No direct file system access outside migration folder
4. No network access except configured GenAI providers

## Performance Considerations

### Migration Execution

**Optimization Strategies**:
1. **Batch Operations**: Provide bulk import helpers for large datasets
2. **Progress Logging**: Log progress every N entities for long migrations
3. **Async Operations**: Use async/await for I/O operations
4. **Memory Management**: Stream large CSV/Excel files instead of loading entirely

**Example Batch Helper**:
```python
async def bulk_create_entities(
    self,
    entities: List[Entity],
    actor_id: str,
    change_description: str,
    batch_size: int = 100
) -> List[Entity]:
    """Create entities in batches for better performance."""
    results = []
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        for entity in batch:
            result = await self.create_entity(entity, actor_id, change_description)
            results.append(result)
        self.log(f"Processed {min(i+batch_size, len(entities))}/{len(entities)} entities")
    return results
```

### Large Data Files

**Handling Strategy**:
- CSV files: Use streaming CSV reader for files > 10MB
- Excel files: Read sheet by sheet for large workbooks
- JSON files: Use streaming JSON parser for large files
- Provide progress callbacks for long-running operations

## Comprehensive Data Update Workflow

This section describes the complete end-to-end workflow for updating data in the Nepal Entity Service through the migration system.

### Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTRIBUTOR WORKFLOW                          │
│                  (Service API Repository)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    1. Create Migration Folder
                       (nes2 migrate create)
                              │
                              ▼
                    2. Add Data Files (CSV/Excel)
                              │
                              ▼
                    3. Write Migration Script
                       (migrate.py)
                              │
                              ▼
                    4. Document Migration
                       (README.md)
                              │
                              ▼
                    5. Submit Pull Request
                       (GitHub PR)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              AUTOMATED BUILD & REVIEW WORKFLOW                   │
│                  (CI/CD + Maintainer Review)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    6. CI: Execute Migration
                       (GitHub Actions)
                              │
                              ▼
                    7. CI: Generate Snapshot Stats
                       (entities/relationships changed)
                              │
                              ▼
                    8. CI: Add Snapshot to PR
                       (commit snapshot files + stats)
                              │
                              ▼
                    9. Maintainer: Review & Approve
                       (review code + snapshot + stats)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              AUTOMATED PERSISTENCE WORKFLOW                      │
│         (Triggered by PR merge or scheduled daily)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    10. Trigger: PR Merge or Schedule
                        (GitHub Actions)
                              │
                              ├─────────────────────────────────┐
                              ▼                                 ▼
                    11a. Check for Persisted     11b. If snapshot exists,
                         Snapshot in Database         skip (deterministic)
                         Repository
                              │
                              ▼
                    12. Execute Migration and Generate Snapshot
                        (creates files in Database repo)
                              │
                              ▼
                    13. Persist Data Snapshot
                        (git commit in Database repo)
                              │
                              ▼
                    14. Push Snapshot to Remote
                        (git push Database repo)
                              │
                              ▼
                    15. Update Submodule Reference
                        (in Service API repo)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA CONSUMPTION                              │
│                  (Public API / Consumers)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    16. Pull Latest Database
                        (git pull Database repo)
                              │
                              ▼
                    17. Serve Updated Data
                        (via API endpoints)
```

### Detailed Workflow Steps

#### Phase 1: Contribution (Steps 1-5)

**Actor**: Community Contributor

**Location**: Service API Repository (fork)

**Steps**:

1. **Create Migration Folder**
   ```bash
   # Fork and clone Service API repo
   git clone https://github.com/contributor/NepalEntityService.git
   cd NepalEntityService
   
   # Create migration from template
   nes2 migrate create add-new-ministers
   # Creates: migrations/005-add-new-ministers/
   ```

2. **Add Data Files**
   ```bash
   # Copy data files into migration folder
   cp ~/ministers_2024.csv migrations/005-add-new-ministers/
   cp ~/sources.txt migrations/005-add-new-ministers/
   ```

3. **Write Migration Script**
   ```python
   # Edit migrations/005-add-new-ministers/migrate.py
   async def migrate(context):
       ministers = context.read_csv("ministers_2024.csv")
       actor_id = "actor:migration:005-add-new-ministers"
       
       for row in ministers:
           entity = Entity(...)
           await context.create_entity(entity, actor_id, "Import minister")
   ```

4. **Document Migration**
   ```markdown
   # Edit migrations/005-add-new-ministers/README.md
   ## Purpose
   Add 25 new cabinet ministers appointed in 2024
   
   ## Data Sources
   - Official government gazette
   - Ministry website
   ```

5. **Submit Pull Request**
   ```bash
   git checkout -b add-migration-005
   git add migrations/005-add-new-ministers/
   git commit -m "Add migration: 005-add-new-ministers"
   git push origin add-migration-005
   # Create PR on GitHub
   ```

#### Phase 2: Automated Build and Review (Steps 6-9)

**Actor**: CI/CD System (GitHub Actions) + Maintainer

**Location**: Service API Repository (PR branch)

**Steps**:

6. **Automated Migration Execution** (GitHub Actions)
   ```yaml
   # Triggered when PR is created/updated
   # Runs in isolated environment with test database
   
   - name: Execute Migration
     run: |
       # Run migration in dry-run mode first
       nes2 migrate run 005-add-new-ministers --dry-run
       
       # Execute migration and generate snapshot
       nes2 migrate run 005-add-new-ministers --generate-snapshot
   ```

7. **Generate Snapshot Statistics**
   ```python
   # CI system computes changes
   snapshot_stats = {
       "entities_created": 25,
       "entities_updated": 0,
       "entities_deleted": 0,
       "relationships_created": 50,
       "relationships_updated": 0,
       "relationships_deleted": 0,
       "files_changed": 75,
       "migration_duration": "5.2s"
   }
   ```

8. **Generate Snapshot and Post Summary**
   ```bash
   # CI system generates snapshot files (stored temporarily in workflow)
   # Posts summary to PR for maintainer review
   
   # CI posts comment on PR with statistics
   # "Migration executed successfully:
   #  - 25 entities created
   #  - 50 relationships created
   #  - 75 files changed
   #  - Duration: 5.2s
   #  
   #  Snapshot will be persisted to Database Repository upon PR merge.
   #  📊 Detailed logs: [View workflow run](link-to-run)"
   ```

9. **Maintainer Review**
   - Review migration script for correctness
   - Review workflow logs for execution details
   - Verify statistics match expectations (from PR comment)
   - Ensure README is complete
   - Check for security issues
   - **Approve or Request Changes**
   - Note: Actual snapshot will be generated and persisted upon merge

#### Phase 3: Automated Persistence (Steps 10-14)

**Actor**: Automated Service (GitHub Actions or Scheduled Job)

**Location**: Service API Repository + Database Repository

**Steps**:

10. **Trigger Automated Persistence** (on PR merge or scheduled run)
    ```yaml
    # GitHub Actions workflow triggered by:
    # 1. PR merge to main branch
    # 2. Scheduled cron job (e.g., daily at 2 AM)
    
    on:
      push:
        branches: [main]
      schedule:
        - cron: '0 2 * * *'  # Daily at 2 AM UTC
    ```

11. **Check for Persisted Snapshot**
    ```python
    # Automated service checks Database Repository
    applied = await migration_manager.get_applied_migrations()
    pending = await migration_manager.get_pending_migrations()
    
    if len(pending) == 0:
        print("No pending migrations, exiting")
        return  # Deterministic behavior
    
    # Process each pending migration
    for migration in pending:
        await process_migration(migration)
    ```

12. **Execute Migration and Generate Snapshot**
    ```python
    # Execute migration script to generate snapshot
    # (migration was already validated during PR review)
    context = MigrationContext(...)
    await migration_script.migrate(context)
    
    # Creates entity files directly in Database Repository
    # nes-db/v2/entity/person/minister-ram-kumar-sharma.json
    # nes-db/v2/entity/person/minister-sita-devi-patel.json
    # ... (23 more files)
    
    # Creates 25 entity files in nes-db/v2/entity/person/
    ```

13. **Persist Data Snapshot**
    ```bash
    # Automated service commits to Database Repository
    cd nes-db/
    git add v2/entity/person/minister-*.json
    git commit -m "Migration: 005-add-new-ministers
    
    Added 25 new cabinet ministers from 2024
    
    Author: contributor@example.com
    Date: 2024-01-25
    Entities created: 25
    Relationships created: 50
    Duration: 5.2s
    Approved by: maintainer@example.com"
    ```

14. **Push Snapshot to Remote**
    ```bash
    # Automated service pushes to Database Repository
    git push origin main
    # Snapshot now available to all consumers
    ```

15. **Update Submodule Reference**
    ```bash
    # Return to Service API repo
    cd ..
    
    # Automated service updates submodule reference
    git add nes-db/
    git commit -m "Update database submodule after migration 005"
    git push origin main
    ```

#### Phase 4: Data Consumption (Steps 16-17)

**Actor**: API Server / Data Consumer

**Location**: Production environment

**Steps**:

16. **Pull Latest Database**
    ```bash
    # Production server pulls latest data (triggered by webhook or scheduled)
    cd /var/www/NepalEntityService/
    git pull origin main
    git submodule update --remote nes-db/
    # Now has latest persisted snapshot with 25 new ministers
    ```

17. **Serve Updated Data**
    ```bash
    # API server reloads database
    systemctl restart nepal-entity-service
    
    # New data available via API
    curl https://api.nepalentity.org/entities/person/minister-ram-kumar-sharma
    # Returns newly added minister data
    ```

### Workflow Characteristics

**Automation**:
- CI automatically executes migrations on PR creation (step 6)
- CI generates snapshots and statistics for review (steps 7-8)
- Automated service persists approved migrations (steps 10-15)
- Scheduled job runs daily to process pending migrations (step 10)

**Separation of Concerns**:
- Contributors work only with Service API repo (lightweight)
- CI system executes migrations in isolated environment
- Maintainers review code and generated snapshots
- Automated service handles persistence to Database repo
- Consumers pull from Database repo (get data snapshots)

**Determinism**:
- Step 11 ensures migrations only run once
- Persisted snapshot (step 13) serves as proof of execution
- Re-running step 10 will skip to step 11b (no-op)
- Pre-generated snapshots from CI ensure consistency

**Auditability**:
- Every data change has a migration script (step 3)
- Every migration has documentation (step 4)
- Every PR includes generated snapshot for review (step 8)
- Every execution creates a commit (step 13)
- Full history available via `git log` in Database repo

**Scalability**:
- Service API repo stays small (only migration scripts)
- Database repo can grow to millions of files
- Consumers can use shallow clones for faster pulls
- Scheduled job processes multiple migrations in batch

**Safety**:
- Code review before approval (step 9)
- Statistics validation before approval (step 9)
- No automatic persistence until PR approved
- Isolated CI environment prevents production impact
- Linear migration sequence prevents conflicts

**Efficiency**:
- Migration validated during PR review (step 7)
- Migration executed once during persistence (step 12)
- Scheduled job reduces manual intervention
- Snapshots stored permanently in Database Repository

## CI/CD Architecture

### GitHub Actions Workflows

The migration system uses two GitHub Actions workflows:

#### 1. Migration Preview Workflow (on PR)

**Trigger**: Pull request created or updated

**Purpose**: Execute migration and generate snapshot for review

**Workflow**:
```yaml
name: Migration Preview

on:
  pull_request:
    paths:
      - 'migrations/**'

jobs:
  preview-migration:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          submodules: true
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
      
      - name: Detect new migrations
        id: detect
        run: |
          # Find migrations added in this PR
          NEW_MIGRATIONS=$(git diff origin/main --name-only | grep "migrations/" | cut -d'/' -f2 | sort -u)
          echo "migrations=$NEW_MIGRATIONS" >> $GITHUB_OUTPUT
      
      - name: Execute migrations
        run: |
          for migration in ${{ steps.detect.outputs.migrations }}; do
            echo "Executing migration: $migration"
            nes2 migrate run $migration --generate-snapshot
          done
      
      - name: Generate statistics
        id: stats
        run: |
          # Compute changes from snapshot
          python scripts/compute_migration_stats.py
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const runUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Migration Preview\n\n${{ steps.stats.outputs.summary }}\n\nSnapshot will be persisted to Database Repository upon PR merge.\n\n📊 [View detailed logs](${runUrl})`
            })
```

#### 2. Migration Persistence Workflow (on merge or schedule)

**Trigger**: 
- PR merged to main branch
- Scheduled daily at 2 AM UTC

**Purpose**: Persist approved migrations to Database Repository

**Workflow**:
```yaml
name: Migration Persistence

on:
  push:
    branches: [main]
    paths:
      - 'migrations/**'
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  persist-migrations:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          submodules: true
          token: ${{ secrets.DATABASE_REPO_TOKEN }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
      
      - name: Check for pending migrations
        id: pending
        run: |
          PENDING=$(nes2 migrate pending --format=json)
          echo "migrations=$PENDING" >> $GITHUB_OUTPUT
      
      - name: Apply pending migrations
        if: steps.pending.outputs.migrations != '[]'
        run: |
          # Execute each pending migration and persist to Database Repository
          nes2 migrate apply-pending --auto-commit
      
      - name: Push to Database Repository
        if: steps.pending.outputs.migrations != '[]'
        run: |
          cd nes-db/
          git push origin main
      
      - name: Update submodule reference
        if: steps.pending.outputs.migrations != '[]'
        run: |
          git add nes-db/
          git commit -m "Update database submodule after migrations"
          git push origin main
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Migration Persistence Failed',
              body: 'Automated migration persistence failed. Please investigate.'
            })
```

### Snapshot Storage

**Location**: Database Repository (nes-db/)

Migration snapshots are stored as the actual entity and relationship files in the Database Repository. When a migration executes, it creates or modifies JSON files through the Publication Service, which writes them to the standard locations in the Database Repository.

**Structure** (in Database Repository):
```
nes-db/
├── v2/
│   ├── entity/
│   │   ├── person/
│   │   │   ├── ram-chandra-poudel.json         (existing)
│   │   │   ├── sher-bahadur-deuba.json         (existing)
│   │   │   ├── minister-ram-kumar-sharma.json  (created by migration 005)
│   │   │   ├── minister-sita-devi-patel.json   (created by migration 005)
│   │   │   └── ... (23 more files from migration 005)
│   │   ├── organization/
│   │   │   └── ...
│   │   └── location/
│   │       └── ...
│   ├── relationship/
│   │   ├── membership-minister-ram-to-party.json  (created by migration 005)
│   │   └── ... (49 more relationship files from migration 005)
│   ├── version/
│   │   ├── entity/
│   │   │   ├── person/
│   │   │   │   ├── minister-ram-kumar-sharma/
│   │   │   │   │   └── v1.json  (version record from migration 005)
│   │   │   │   └── ...
│   │   └── relationship/
│   │       └── ...
│   └── actor/
│       ├── migration-005-add-ministers.json  (actor record for migration)
│       └── ...
└── .git/
    └── (Git history with migration commits)
```

**Snapshot = Data Files**:
- Migration snapshots are NOT separate files
- Snapshots ARE the entity/relationship/version JSON files themselves
- Each migration creates/modifies files in standard locations
- Publication Service handles file writing (same as manual updates)

**File Locations** (determined by Publication Service):
- **Entities**: `v2/entity/{type}/{slug}.json`
- **Relationships**: `v2/relationship/{id}.json`
- **Versions**: `v2/version/entity/{type}/{slug}/v{N}.json`
- **Actors**: `v2/actor/{actor-id}.json`

**Git Commit** (in Database Repository):
```
commit abc123def456...
Author: Migration Bot <bot@nepalentity.org>
Date: 2024-01-25 10:30:00 +0000

Migration: 005-add-new-ministers

Added 25 new cabinet ministers from 2024

Author: contributor@example.com
Date: 2024-01-25
Entities created: 25
Relationships created: 50
Duration: 5.2s
Approved by: maintainer@example.com
PR: #42
```

**Design Decision**: Migration snapshots are the actual data files (not separate snapshot files) because:
- **Single Source of Truth**: No duplication between snapshots and data
- **Standard Structure**: Uses same file structure as manual updates
- **Publication Service**: Migrations use same service as manual updates
- **Permanent Storage**: Data persisted in Git permanently
- **Complete History**: Git log shows all migrations and their data changes
- **Determinism**: Checking for persisted snapshots = checking if files exist in Git
- **Linear Evolution**: Migrations applied sequentially, no forking or merging
- **Distribution**: Anyone can clone Database repo and get all data
- **Audit Trail**: Each migration commit shows exactly what files were created/modified

**Workflow**:
1. **PR Review**: CI validates migration, posts statistics
2. **PR Merge**: Automated service executes migration
3. **Migration Execution**: Migration calls Publication Service to create entities
4. **File Creation**: Publication Service writes JSON files to nes-db/v2/
5. **Persistence**: Files committed to Database Repository (this IS the snapshot)
6. **Distribution**: Commit pushed to remote, available to all consumers

**Example**: Migration 005 creates 25 ministers
- Creates 25 files in `nes-db/v2/entity/person/minister-*.json`
- Creates 50 files in `nes-db/v2/relationship/*.json`
- Creates 25 files in `nes-db/v2/version/entity/person/minister-*/v1.json`
- Creates 1 file in `nes-db/v2/actor/migration-005-add-ministers.json`
- All 101 files committed in single Git commit
- This commit IS the migration snapshot

## Contributor Workflow

### Creating a Migration

**Step-by-Step Process for Contributors**:

1. **Fork and Clone Service API Repository**
   ```bash
   # Fork on GitHub, then clone
   git clone https://github.com/your-username/NepalEntityService.git
   cd NepalEntityService
   ```

2. **Create Migration Folder**
   ```bash
   # Use CLI to create migration from template
   nes2 migrate create add-new-politicians
   
   # This creates: migrations/003-add-new-politicians/
   # - migrate.py (template script)
   # - README.md (template documentation)
   ```

3. **Add Data Files**
   ```bash
   # Add your data files to migration folder
   cp ~/politicians.csv migrations/003-add-new-politicians/
   ```

4. **Implement Migration Script**
   ```python
   # Edit migrations/003-add-new-politicians/migrate.py
   # Implement logic to read CSV and create entities
   ```

5. **Document Migration**
   ```markdown
   # Edit migrations/003-add-new-politicians/README.md
   # Document purpose, data sources, and expected changes
   ```

6. **Test Locally (Optional)**
   ```bash
   # Validate migration structure
   nes2 migrate validate 003-add-new-politicians
   
   # Test in dry-run mode (if you have database setup)
   nes2 migrate run 003-add-new-politicians --dry-run
   ```

7. **Submit Pull Request**
   ```bash
   git checkout -b add-migration-003
   git add migrations/003-add-new-politicians/
   git commit -m "Add migration: 003-add-new-politicians"
   git push origin add-migration-003
   # Create PR on GitHub
   ```

**What Contributors Need**:
- Fork of Service API Repository
- Python environment with nes2 package installed
- Data files (CSV, Excel, JSON) to import
- Basic understanding of Entity data model
- NO access to Database Repository required

**What Contributors Don't Need**:
- Access to Database Repository
- Ability to execute migrations (maintainers do this)
- Large disk space for database files

**Design Decision**: The contributor workflow is designed to be as simple as possible. Contributors only interact with the Service API Repository, which is lightweight and easy to clone. The `nes2 migrate create` command provides templates and scaffolding, lowering the barrier to entry. Contributors don't need to set up the full database or execute migrations—they only need to write and test the migration script logic.

## Deployment and Rollout

### Phase 1: Core Infrastructure (Week 1-2)
- Implement Migration Manager (discovery, tracking)
- Implement Migration Runner (execution)
- Implement Migration Context (API for scripts)
- Create migration history storage
- Add CLI commands

### Phase 2: Helper Functions and Templates (Week 3)
- Implement CSV/Excel/JSON readers
- Create bulk import helpers
- Create migration templates
- Write documentation and examples

### Phase 3: GenAI Integration (Week 4)
- Integrate GenAI providers
- Add non-deterministic migration support
- Create GenAI helper functions
- Add GenAI examples

### Phase 4: Testing and Documentation (Week 5)
- Write comprehensive tests
- Create contributor documentation
- Create maintainer documentation
- Add example migrations

## Future Enhancements

### Potential Improvements

1. **Migration Dependencies**: Allow migrations to declare dependencies on other migrations
2. **Parallel Execution**: Run independent migrations in parallel
3. **Migration Rollback**: Implement optional rollback functions in migrations
4. **Migration Branching**: Support multiple migration branches for different environments
5. **Web UI**: Create web interface for viewing migration history and status
6. **Automated Testing**: Run migrations against test database in CI/CD
7. **Migration Linting**: Automated checks for common migration issues
8. **Performance Profiling**: Track and optimize slow migrations

### Extensibility Points

1. **Custom Validators**: Allow custom validation rules for migrations
2. **Custom Helpers**: Plugin system for domain-specific helper functions
3. **Custom Reporters**: Different output formats for migration results
4. **Custom Storage**: Alternative storage backends for migration history
