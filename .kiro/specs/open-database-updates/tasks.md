# Implementation Plan

## Overview

This implementation plan breaks down the Open Database Updates feature into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, with the final result being a complete migration system with CI/CD automation.

## Tasks

- [x] 1. Set up migration infrastructure and core models
  - Create migration service package structure
  - Define Migration and MigrationResult data models
  - Implement migration folder naming conventions and validation
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.4_

- [x] 1.1 Create migration service package
  - Create `nes2/services/migration/` directory
  - Add `__init__.py` with package exports
  - _Requirements: 1.1_

- [x] 1.2 Define migration data models
  - Create `nes2/services/migration/models.py`
  - Implement `Migration` dataclass with prefix, name, folder_path, script_path, metadata
  - Implement `MigrationResult` dataclass with status, duration, statistics, error
  - Implement `MigrationStatus` enum (RUNNING, COMPLETED, FAILED, SKIPPED)
  - _Requirements: 1.1, 1.2, 2.4_

- [x] 1.3 Implement migration folder validation
  - Create `nes2/services/migration/validation.py`
  - Implement function to validate migration folder structure (has migrate.py, README.md)
  - Implement function to validate migration naming convention (NNN-descriptive-name)
  - Implement function to validate migration metadata (AUTHOR, DATE, DESCRIPTION)
  - _Requirements: 2.1, 2.2, 2.4, 5.2_

- [ ] 2. Implement Migration Manager for discovery and tracking
  - Implement migration discovery from migrations/ directory
  - Implement checking for persisted snapshots in Database Repository
  - Implement pending migrations detection
  - _Requirements: 1.1, 1.2, 1.4, 1.8, 6.8_

- [x] 2.1 Implement migration discovery
  - Create `nes2/services/migration/manager.py`
  - Implement `MigrationManager` class with `discover_migrations()` method
  - Scan migrations/ directory for folders matching NNN-* pattern
  - Sort migrations by numeric prefix
  - Load migration metadata from script files
  - _Requirements: 1.1, 1.2, 5.1_

- [x] 2.2 Implement persisted snapshot checking
  - Implement `get_applied_migrations()` method in MigrationManager
  - Query Git log in Database Repository for migration commits
  - Parse commit messages to extract migration names
  - Cache results to avoid repeated Git queries
  - _Requirements: 1.4, 6.7, 6.8_

- [x] 2.3 Implement pending migrations detection
  - Implement `get_pending_migrations()` method in MigrationManager
  - Compare discovered migrations with applied migrations
  - Return migrations that haven't been applied yet
  - Implement `is_migration_applied()` method for single migration check
  - _Requirements: 1.2, 6.8_

- [x] 3. Implement Migration Context for script execution
  - Create thin context with service access
  - Implement file reading helpers (CSV, JSON, Excel)
  - Implement logging mechanism
  - _Requirements: 2.5, 2.6, 3.6_

- [x] 3.1 Create Migration Context class
  - Create `nes2/services/migration/context.py`
  - Implement `MigrationContext` class with service references
  - Provide direct access to publication, search, scraping, and db services
  - Provide migration_dir property
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3_

- [x] 3.2 Implement file reading helpers
  - Implement `read_csv()` method with CSV parsing
  - Implement `read_json()` method with JSON parsing
  - Implement `read_excel()` method with Excel parsing
  - Handle file not found errors gracefully
  - _Requirements: 2.5, 2.6, 3.6_

- [x] 3.3 Implement logging mechanism
  - Implement `log()` method for migration progress logging
  - Store logs in context for later retrieval
  - Print logs to console during execution
  - _Requirements: 6.6_

- [ ] 4. Implement Migration Runner for execution
  - Implement migration script loading and execution
  - Implement deterministic execution (check before run)
  - Implement error handling and logging
  - _Requirements: 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 6.5, 6.6, 6.7, 6.8_

- [ ] 4.1 Create Migration Runner class
  - Create `nes2/services/migration/runner.py`
  - Implement `MigrationRunner` class with service dependencies
  - Implement `create_context()` method to build MigrationContext
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 4.2 Implement migration script loading
  - Implement `_load_script()` method to dynamically import migrate.py
  - Validate script has `migrate()` function
  - Validate script has required metadata (AUTHOR, DATE, DESCRIPTION)
  - Handle syntax errors gracefully
  - _Requirements: 1.7, 2.4, 6.6_

- [ ] 4.3 Implement deterministic execution
  - Implement `run_migration()` method with determinism check
  - Check if migration already applied before execution
  - Skip execution if persisted snapshot exists (return SKIPPED status)
  - Support force flag to allow re-execution
  - _Requirements: 6.1, 6.7, 6.8_

- [ ] 4.4 Implement migration execution
  - Execute migration script's `migrate()` function with context
  - Track execution time
  - Capture logs from context
  - Handle all exceptions and create MigrationResult
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.5, 6.6_

- [ ] 4.5 Implement batch migration execution
  - Implement `run_migrations()` method for multiple migrations
  - Execute migrations in sequential order
  - Skip already-applied migrations
  - Stop on first failure or continue based on flag
  - _Requirements: 1.2, 6.2_

- [ ] 5. Implement Git integration for persistence
  - Implement commit creation with migration metadata
  - Implement batch commits for large migrations
  - Implement push to remote Database Repository
  - _Requirements: 1.3, 1.5, 6.3, 6.4, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.5_

- [ ] 5.1 Implement commit creation
  - Implement `commit_and_push()` method in MigrationRunner
  - Format commit message with migration metadata
  - Stage changed files in Database Repository
  - Create Git commit with formatted message
  - _Requirements: 1.3, 1.5, 6.3, 7.1, 7.2, 7.3, 7.5_

- [ ] 5.2 Implement batch commits
  - Detect when migration creates more than 1000 files
  - Split commits into batches of 1000 files each
  - Create multiple commits with batch metadata
  - _Requirements: 8.1, 8.2_

- [ ] 5.3 Implement push to remote
  - Push commits to remote Database Repository
  - Handle push failures gracefully
  - Use appropriate timeout for large pushes
  - _Requirements: 6.4, 8.5_

- [ ] 5.4 Implement Git configuration
  - Configure Git settings for large repositories
  - Set core.preloadindex, core.fscache, gc.auto
  - _Requirements: 8.4_

- [ ] 6. Implement CLI commands
  - Implement `nes2 migrate list` command
  - Implement `nes2 migrate pending` command
  - Implement `nes2 migrate run` command
  - Implement `nes2 migrate create` command
  - _Requirements: 1.6, 5.3, 5.4, 6.1, 6.2_

- [ ] 6.1 Implement migrate list command
  - Create `nes2/cli/migrate.py` with Click command group
  - Implement `list` command to show all migrations with status
  - Display migration metadata (author, date, description)
  - Show applied vs pending status
  - _Requirements: 1.6_

- [ ] 6.2 Implement migrate pending command
  - Implement `pending` command to show only pending migrations
  - Display migration metadata
  - Show count of pending migrations
  - _Requirements: 1.6_

- [ ] 6.3 Implement migrate run command
  - Implement `run` command to execute specific migration
  - Support `--all` flag to run all pending migrations
  - Support `--dry-run` flag to skip persistence
  - Support `--force` flag to allow re-execution
  - Display progress and results
  - _Requirements: 6.1, 6.2_

- [ ] 6.4 Implement migrate create command
  - Implement `create` command to generate migration folder from template
  - Determine next available prefix number
  - Create migration folder with NNN-descriptive-name format
  - Copy template migrate.py with pre-filled metadata
  - Copy template README.md
  - _Requirements: 5.3, 5.4_

- [ ] 7. Create migration templates
  - Create template migrate.py with documentation
  - Create template README.md with structure
  - _Requirements: 2.3, 5.3, 5.4_

- [ ] 7.1 Create migrate.py template
  - Create `nes2/services/migration/templates/migrate.py.template`
  - Include metadata placeholders (AUTHOR, DATE, DESCRIPTION)
  - Include comprehensive documentation of context methods
  - Include example code patterns
  - _Requirements: 2.3, 5.3_

- [ ] 7.2 Create README.md template
  - Create `nes2/services/migration/templates/README.md.template`
  - Include sections for Purpose, Data Sources, Changes, Dependencies, Notes
  - _Requirements: 2.3, 5.3_

- [ ] 8. Implement CI/CD workflows
  - Create GitHub Actions workflow for migration preview
  - Create GitHub Actions workflow for migration persistence
  - _Requirements: 6.2, 6.3, 6.4, 7.4_

- [ ] 8.1 Create migration preview workflow
  - Create `.github/workflows/migration-preview.yml`
  - Trigger on pull request to migrations/ directory
  - Execute migrations in isolated environment
  - Generate statistics (entities/relationships created)
  - Post comment on PR with statistics and logs link
  - _Requirements: 6.2, 6.3, 7.4_

- [ ] 8.2 Create migration persistence workflow
  - Create `.github/workflows/migration-persistence.yml`
  - Trigger on PR merge to main branch
  - Trigger on schedule (daily at 2 AM UTC)
  - Check for pending migrations
  - Execute pending migrations
  - Commit to Database Repository
  - Push to remote
  - Update submodule reference in Service API Repository
  - _Requirements: 6.2, 6.3, 6.4, 7.4_

- [ ] 9. Add documentation
  - Write contributor guide for creating migrations
  - Write maintainer guide for reviewing and executing migrations
  - Document migration system architecture
  - _Requirements: 5.3_

- [ ] 9.1 Write contributor documentation
  - Create `docs/migration-contributor-guide.md`
  - Document step-by-step process for creating migrations
  - Include examples of common migration patterns
  - Document how to test migrations locally
  - _Requirements: 5.3_

- [ ] 9.2 Write maintainer documentation
  - Create `docs/migration-maintainer-guide.md`
  - Document PR review process
  - Document how to execute migrations
  - Document troubleshooting common issues
  - _Requirements: 5.3_

- [ ] 9.3 Write architecture documentation
  - Create `docs/migration-architecture.md`
  - Document two-repository architecture
  - Document linear migration model
  - Document determinism through persisted snapshots
  - _Requirements: 1.3, 1.8_
