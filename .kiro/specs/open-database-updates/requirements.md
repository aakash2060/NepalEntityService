# Requirements Document

## Introduction

The Nepal Entity Service currently operates with a read-only public API where trusted data maintainers perform updates locally through the Publication Service. This feature introduces an open contribution model based on versioned migration folders that enables community members to propose data changes while maintaining a complete, reproducible history of database evolution through Git.

The system operates across two GitHub repositories:
- **Service API Repository**: https://github.com/NewNepal-org/NepalEntityService (containing application code and migrations)
- **Database Repository**: https://github.com/NewNepal-org/NepalEntityService-database (containing 100k-1M entity/relationship JSON files, mounted as Git submodule at `nes-db/`)

Contributors submit migration folders via GitHub pull requests to the Service API Repository. Maintainers review and merge them. When migrations are executed, they modify files in the Database Repository, which are then committed with detailed metadata. This two-repo architecture allows the large database to be managed independently while keeping the service code lightweight.

Migration history is tracked through Git commits in the Database Repository rather than a separate tracking system. Each migration execution creates a Git commit with author, date, and statistics. This approach leverages Git's distributed version control for complete audit trails, rollback capabilities via `git revert`, and transparent history.

## Glossary

- **Migration**: A versioned folder containing an executable Python script and supporting files (CSVs, Excel, README, etc.) that applies a specific set of data changes to the Entity_Database
- **Migration_Script**: The main Python script (migrate.py or run.py) within a migration folder that performs the data changes
- **Migration_System**: System for discovering and executing migrations in sequential order
- **Migration_Prefix**: Numeric prefix (e.g., 000, 001, 002) that determines execution order of migrations
- **Migration_Assets**: Supporting files within a migration folder (CSV data files, Excel spreadsheets, documentation)
- **Service_API_Repository**: GitHub repository at https://github.com/NewNepal-org/NepalEntityService containing the application code and migration scripts
- **Database_Repository**: GitHub repository at https://github.com/NewNepal-org/NepalEntityService-database containing the actual entity/relationship JSON files, managed as a Git submodule at `nes-db/` in the Service_API_Repository
- **Contributor**: Any person who submits migration scripts via GitHub pull requests
- **Maintainer**: Trusted person who reviews and merges migration script pull requests and executes migrations

## Requirements

### Requirement 1

**User Story:** As a data maintainer, I want to manage database evolution through versioned migration folders across two Git repositories, so that I can track, reproduce, and audit how the database content has changed over time.

#### Acceptance Criteria

1. THE Migration_System SHALL support sequential migration folders with numeric prefixes (000-initial-locations/, 001-update-location-names/) in the Service_API_Repository
2. THE Migration_System SHALL execute migrations in sequential order based on their numeric prefix
3. THE Migration_System SHALL store migration folders in the Service_API_Repository and entity data in the Database_Repository
4. WHEN a migration is executed, THE Migration_System SHALL commit changes to the Database_Repository with migration metadata in the commit message
5. THE Migration_System SHALL include author, date, entities created/updated, and duration in Git commit messages
6. THE Migration_System SHALL provide a command to list all available migrations with their metadata
7. THE Migration_System SHALL look for a main script file (migrate.py or run.py) within each migration folder to execute
8. THE Migration_System SHALL manage the Database_Repository as a Git submodule within the Service_API_Repository

### Requirement 2

**User Story:** As a migration author, I want to organize migrations as folders with supporting files and metadata, so that I can include data files, documentation, and authorship information together in one place.

#### Acceptance Criteria

1. THE Migration_System SHALL support migration folders containing multiple files and subdirectories
2. THE Migration_System SHALL allow migrations to include CSV files, Excel spreadsheets, JSON files, and other data formats
3. THE Migration_System SHALL require migrations to include README.md files documenting the migration purpose and approach
4. THE Migration_System SHALL require migration scripts to define AUTHOR, DATE, and DESCRIPTION metadata constants
5. THE Migration_System SHALL allow migration scripts to reference files within their migration folder using relative paths
6. THE Migration_System SHALL provide the migration folder path to the migration script at runtime
7. THE Migration_System SHALL use migration metadata for Git commit messages when changes are committed to the Database_Repository

### Requirement 3

**User Story:** As a migration script author, I want to write migration scripts that can create, update, and delete entities and relationships, so that I can make any necessary data changes to the database.

#### Acceptance Criteria

1. THE Migration_System SHALL provide a migration script API for creating new entities through the Publication_Service
2. THE Migration_System SHALL provide a migration script API for updating existing entities through the Publication_Service
3. THE Migration_System SHALL provide a migration script API for creating and updating relationships through the Publication_Service
4. THE Migration_System SHALL provide a migration script API for querying existing entities and relationships
5. THE Migration_System SHALL ensure all migration operations go through the Publication_Service for proper versioning and validation
6. THE Migration_System SHALL provide helper functions for reading CSV, Excel, and JSON files from migration folders

### Requirement 4

**User Story:** As a migration script author, I want to access existing services in my migrations, so that I can leverage scraping, search, and publication capabilities for data processing.

#### Acceptance Criteria

1. THE Migration_System SHALL provide migration scripts with access to the Scraping_Service for data extraction and normalization
2. THE Migration_System SHALL provide migration scripts with access to the Search_Service for querying existing entities
3. THE Migration_System SHALL provide migration scripts with access to the Publication_Service for creating and updating entities
4. THE Migration_System SHALL handle service failures gracefully with error reporting

### Requirement 5

**User Story:** As a community member, I want to contribute migrations via GitHub pull requests, so that I can propose data improvements that maintainers can review and merge.

#### Acceptance Criteria

1. THE Migration_System SHALL store migrations in a dedicated directory (migrations/) in the Service_API_Repository
2. THE Migration_System SHALL enforce naming conventions for migration folders (NNN-descriptive-name/ format)
3. THE Migration_System SHALL provide documentation and templates for creating migration folders
4. THE Migration_System SHALL provide a template migration folder structure for contributors to copy

### Requirement 6

**User Story:** As a maintainer, I want to execute migrations and commit changes to Git, so that I can apply community contributions to the database.

#### Acceptance Criteria

1. THE Migration_System SHALL provide a command to execute a specific migration by name
2. THE Migration_System SHALL provide a command to execute all migrations in sequential order
3. WHEN a migration completes successfully, THE Migration_System SHALL commit changes to the Database_Repository with formatted commit message
4. THE Migration_System SHALL push commits to the remote Database_Repository after successful migration execution
5. WHEN a migration fails, THE Migration_System SHALL NOT commit changes to the Database_Repository
6. THE Migration_System SHALL log detailed error information including stack traces for failed migrations
7. WHEN a migration is executed, THE Migration_System SHALL persist the resulting data snapshot in the Database_Repository so that re-running the migration becomes deterministic
8. THE Migration_System SHALL prevent re-execution of already-applied migrations by checking persisted snapshots in the Database_Repository

### Requirement 7

**User Story:** As a data maintainer, I want to track the provenance of all data changes through Git history, so that I can understand the source and reasoning behind every modification.

#### Acceptance Criteria

1. WHEN a migration creates or updates an entity, THE Publication_Service SHALL record the migration script name as the actor
2. THE Migration_System SHALL preserve contributor attribution from the migration script metadata in Git commits
3. THE Migration_System SHALL link version records to the specific migration that created them through actor attribution
4. THE Migration_System SHALL maintain a complete audit trail through Git history in the Database_Repository
5. THE Migration_System SHALL format Git commit messages with migration metadata including author, date, and statistics

### Requirement 8

**User Story:** As a system administrator, I want to efficiently manage the large Database Repository containing 100k-1M files, so that Git operations remain performant and practical.

#### Acceptance Criteria

1. THE Migration_System SHALL support batch commits when migrations create or modify large numbers of files
2. THE Migration_System SHALL commit changes in batches of up to 1000 files per commit when appropriate
3. THE Migration_System SHALL provide documentation for using shallow clones and sparse checkout with the Database_Repository
4. THE Migration_System SHALL configure Git settings optimized for large repositories (core.preloadindex, core.fscache, gc.auto)
5. THE Migration_System SHALL handle Git push operations for large commits with appropriate timeouts
