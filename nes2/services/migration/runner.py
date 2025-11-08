"""
Migration Runner for executing migration scripts.

This module provides the MigrationRunner class which handles:
- Loading and executing migration scripts
- Creating migration contexts for script execution
- Tracking execution statistics (entities/relationships created)
- Error handling and logging
- Deterministic execution (checking for persisted snapshots)
"""

import importlib.util
import inspect
import logging
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import List, Optional

from nes2.database.entity_database import EntityDatabase
from nes2.services.migration.context import MigrationContext
from nes2.services.migration.manager import MigrationManager
from nes2.services.migration.models import Migration, MigrationResult, MigrationStatus
from nes2.services.publication.service import PublicationService
from nes2.services.scraping.service import ScrapingService
from nes2.services.search.service import SearchService

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Executes migration scripts and manages Git operations.
    
    The MigrationRunner is responsible for:
    - Loading migration scripts dynamically
    - Creating execution contexts with service access
    - Executing migration scripts with error handling
    - Tracking execution statistics
    - Checking for persisted snapshots to ensure determinism
    - Managing batch execution of multiple migrations
    """
    
    def __init__(
        self,
        publication_service: PublicationService,
        search_service: SearchService,
        scraping_service: ScrapingService,
        db: EntityDatabase,
        migration_manager: MigrationManager,
    ):
        """
        Initialize the Migration Runner.
        
        Args:
            publication_service: Service for creating/updating entities and relationships
            search_service: Service for searching and querying entities
            scraping_service: Service for data extraction and normalization
            db: Database for direct read access to entities
            migration_manager: Manager for discovering and tracking migrations
        """
        self.publication = publication_service
        self.search = search_service
        self.scraping = scraping_service
        self.db = db
        self.manager = migration_manager
        
        # Configure Git for large repositories
        self._configure_git_for_large_repos()
        
        logger.info("MigrationRunner initialized")
    
    def _configure_git_for_large_repos(self) -> None:
        """
        Configure Git settings optimized for large repositories.
        
        Sets the following Git configuration options in the Database Repository:
        - core.preloadindex: Enable parallel index preloading for faster operations
        - core.fscache: Enable file system cache on Windows
        - gc.auto: Disable automatic garbage collection (run manually)
        
        These settings improve Git performance when working with repositories
        containing 100k-1M files.
        """
        db_repo_path = self.manager.db_repo_path
        
        # Check if database repository exists and is a Git repository
        if not db_repo_path.exists():
            logger.warning(
                f"Database repository does not exist: {db_repo_path}. "
                "Skipping Git configuration."
            )
            return
        
        git_dir = db_repo_path / ".git"
        if not git_dir.exists():
            logger.warning(
                f"Database repository is not a Git repository: {db_repo_path}. "
                "Skipping Git configuration."
            )
            return
        
        # Git configuration settings for large repositories
        git_configs = {
            "core.preloadindex": "true",
            "core.fscache": "true",
            "gc.auto": "0",  # Disable auto GC
        }
        
        logger.info("Configuring Git for large repository operations")
        
        for config_key, config_value in git_configs.items():
            try:
                subprocess.run(
                    ["git", "config", config_key, config_value],
                    cwd=db_repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
                logger.debug(f"Set Git config: {config_key}={config_value}")
            
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout setting Git config: {config_key}")
            
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to set Git config {config_key}: {e.stderr}")
            
            except Exception as e:
                logger.warning(f"Unexpected error setting Git config {config_key}: {e}")
        
        logger.info("Git configuration complete")
    
    def create_context(self, migration: Migration) -> MigrationContext:
        """
        Create execution context for migration script.
        
        The context provides the migration script with:
        - Access to publication, search, and scraping services
        - Access to the database for read operations
        - File reading helpers (CSV, JSON, Excel)
        - Logging mechanism
        - Path to the migration folder
        
        Args:
            migration: Migration to create context for
        
        Returns:
            MigrationContext instance ready for script execution
        
        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> context = runner.create_context(migration)
            >>> # Pass context to migration script
            >>> await migrate(context)
        """
        logger.debug(f"Creating context for migration {migration.full_name}")
        
        context = MigrationContext(
            publication_service=self.publication,
            search_service=self.search,
            scraping_service=self.scraping,
            db=self.db,
            migration_dir=migration.folder_path,
        )
        
        return context
    
    def _load_script(self, migration: Migration) -> tuple:
        """
        Load migration script dynamically and validate it.
        
        This method:
        - Dynamically imports the migration script (migrate.py or run.py)
        - Validates that the script has a migrate() function
        - Validates that the script has required metadata (AUTHOR, DATE, DESCRIPTION)
        - Handles syntax errors gracefully
        
        Args:
            migration: Migration to load script for
        
        Returns:
            Tuple of (migrate_function, metadata_dict)
        
        Raises:
            ValueError: If script is invalid or missing required components
            SyntaxError: If script has syntax errors
        
        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> migrate_func, metadata = runner._load_script(migration)
            >>> await migrate_func(context)
        """
        logger.debug(f"Loading script for migration {migration.full_name}")
        
        script_path = migration.script_path
        
        if not script_path.exists():
            raise ValueError(f"Migration script not found: {script_path}")
        
        # Create a unique module name to avoid conflicts
        module_name = f"migration_{migration.full_name.replace('-', '_')}"
        
        try:
            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"Failed to load module spec from {script_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules temporarily to support relative imports
            sys.modules[module_name] = module
            
            try:
                spec.loader.exec_module(module)
            finally:
                # Clean up sys.modules
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            logger.debug(f"Successfully loaded module from {script_path}")
        
        except SyntaxError as e:
            error_msg = (
                f"Syntax error in migration script {migration.full_name}:\n"
                f"  File: {e.filename}\n"
                f"  Line {e.lineno}: {e.text}\n"
                f"  {' ' * (e.offset - 1) if e.offset else ''}^\n"
                f"  {e.msg}"
            )
            logger.error(error_msg)
            raise SyntaxError(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to load migration script {migration.full_name}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate that the module has a migrate() function
        if not hasattr(module, 'migrate'):
            raise ValueError(
                f"Migration script {migration.full_name} must define a 'migrate()' function"
            )
        
        migrate_func = getattr(module, 'migrate')
        
        # Validate that migrate is a function
        if not callable(migrate_func):
            raise ValueError(
                f"'migrate' in {migration.full_name} must be a callable function"
            )
        
        # Validate that migrate is async
        if not inspect.iscoroutinefunction(migrate_func):
            raise ValueError(
                f"'migrate()' function in {migration.full_name} must be async "
                "(defined with 'async def')"
            )
        
        # Extract metadata
        metadata = {
            'author': getattr(module, 'AUTHOR', None),
            'date': getattr(module, 'DATE', None),
            'description': getattr(module, 'DESCRIPTION', None),
        }
        
        # Validate required metadata
        missing_metadata = []
        if not metadata['author']:
            missing_metadata.append('AUTHOR')
        if not metadata['date']:
            missing_metadata.append('DATE')
        if not metadata['description']:
            missing_metadata.append('DESCRIPTION')
        
        if missing_metadata:
            raise ValueError(
                f"Migration script {migration.full_name} is missing required metadata: "
                f"{', '.join(missing_metadata)}"
            )
        
        logger.debug(
            f"Validated migration script {migration.full_name}: "
            f"author={metadata['author']}, date={metadata['date']}"
        )
        
        return migrate_func, metadata
    
    async def run_migration(
        self,
        migration: Migration,
        dry_run: bool = False,
        auto_commit: bool = True,
        force: bool = False
    ) -> MigrationResult:
        """
        Execute a migration script with determinism check.
        
        This method:
        - Checks if migration already applied before execution
        - Skips execution if persisted snapshot exists (returns SKIPPED status)
        - Supports force flag to allow re-execution
        - Executes the migration script with proper context
        - Tracks execution time and statistics
        - Handles all exceptions gracefully
        
        Args:
            migration: Migration to execute
            dry_run: If True, don't commit changes (default: False)
            auto_commit: If True, commit and push changes after execution (default: True)
            force: If True, allow re-execution of already-applied migrations (default: False)
        
        Returns:
            MigrationResult with execution details
        
        Example:
            >>> runner = MigrationRunner(...)
            >>> migration = Migration(...)
            >>> result = await runner.run_migration(migration)
            >>> print(result.status)
            MigrationStatus.COMPLETED
        """
        logger.info(f"Running migration {migration.full_name}")
        
        # Create result object
        result = MigrationResult(
            migration=migration,
            status=MigrationStatus.RUNNING,
        )
        
        # Check if migration already applied (determinism check)
        if not force:
            is_applied = await self.manager.is_migration_applied(migration)
            if is_applied:
                logger.info(
                    f"Migration {migration.full_name} already applied "
                    "(persisted snapshot exists), skipping"
                )
                result.status = MigrationStatus.SKIPPED
                result.logs.append(
                    f"Migration {migration.full_name} already applied, skipping"
                )
                return result
        
        # If force flag is set and migration was applied, log warning
        if force:
            is_applied = await self.manager.is_migration_applied(migration)
            if is_applied:
                logger.warning(
                    f"Force flag set: re-executing already-applied migration "
                    f"{migration.full_name}"
                )
                result.logs.append(
                    f"WARNING: Force re-execution of already-applied migration"
                )
        
        # Load migration script
        try:
            migrate_func, metadata = self._load_script(migration)
            logger.debug(f"Loaded migration script {migration.full_name}")
        except Exception as e:
            logger.error(f"Failed to load migration script: {e}")
            result.status = MigrationStatus.FAILED
            result.error = e
            result.logs.append(f"Failed to load migration script: {e}")
            return result
        
        # Create execution context
        context = self.create_context(migration)
        
        # Track statistics before execution
        entities_before = await self._count_entities()
        relationships_before = await self._count_relationships()
        
        # Execute migration
        start_time = time.time()
        
        try:
            logger.info(f"Executing migration {migration.full_name}...")
            
            # Execute the migrate() function
            await migrate_func(context)
            
            # Calculate execution time
            end_time = time.time()
            result.duration_seconds = end_time - start_time
            
            # Track statistics after execution
            entities_after = await self._count_entities()
            relationships_after = await self._count_relationships()
            
            result.entities_created = entities_after - entities_before
            result.relationships_created = relationships_after - relationships_before
            
            # Capture logs from context (extend, don't replace)
            result.logs.extend(context.logs)
            
            # Mark as completed
            result.status = MigrationStatus.COMPLETED
            
            logger.info(
                f"Migration {migration.full_name} completed successfully in "
                f"{result.duration_seconds:.1f}s "
                f"(created: {result.entities_created} entities, "
                f"{result.relationships_created} relationships)"
            )
            
            # Commit and push changes if auto_commit is enabled
            if auto_commit and not dry_run:
                try:
                    await self.commit_and_push(migration, result, dry_run=False)
                    logger.info(f"Changes committed and pushed for {migration.full_name}")
                except Exception as commit_error:
                    logger.error(f"Failed to commit changes: {commit_error}")
                    # Mark migration as failed if commit fails
                    result.status = MigrationStatus.FAILED
                    result.error = commit_error
                    result.logs.append(f"ERROR: Failed to commit changes: {commit_error}")
        
        except Exception as e:
            # Calculate execution time even on failure
            end_time = time.time()
            result.duration_seconds = end_time - start_time
            
            # Capture error details
            result.status = MigrationStatus.FAILED
            result.error = e
            
            # Capture logs from context (extend, don't replace)
            result.logs.extend(context.logs)
            
            # Add error traceback to logs
            error_traceback = traceback.format_exc()
            result.logs.append(f"ERROR: {e}")
            result.logs.append(f"Traceback:\n{error_traceback}")
            
            logger.error(
                f"Migration {migration.full_name} failed after "
                f"{result.duration_seconds:.1f}s: {e}\n{error_traceback}"
            )
        
        return result
    
    async def _count_entities(self) -> int:
        """
        Count total number of entities in the database.
        
        Returns:
            Total entity count
        """
        try:
            # Use database's list method with a high limit to get count
            # This is a simple implementation - could be optimized with a dedicated count method
            entities = await self.db.list_entities(limit=1000000)
            return len(entities)
        except Exception as e:
            logger.warning(f"Failed to count entities: {e}")
            return 0
    
    async def _count_relationships(self) -> int:
        """
        Count total number of relationships in the database.
        
        Returns:
            Total relationship count
        """
        try:
            # Use database's list method with a high limit to get count
            # This is a simple implementation - could be optimized with a dedicated count method
            relationships = await self.db.list_relationships(limit=1000000)
            return len(relationships)
        except Exception as e:
            logger.warning(f"Failed to count relationships: {e}")
            return 0
    
    async def run_migrations(
        self,
        migrations: List[Migration],
        dry_run: bool = False,
        auto_commit: bool = True,
        stop_on_failure: bool = True
    ) -> List[MigrationResult]:
        """
        Execute multiple migrations in sequential order.
        
        This method:
        - Executes migrations in the order provided (typically sorted by prefix)
        - Skips already-applied migrations automatically
        - Can stop on first failure or continue based on flag
        - Returns results for all migrations (executed, skipped, or failed)
        
        Args:
            migrations: List of migrations to execute (in order)
            dry_run: If True, don't commit changes (default: False)
            auto_commit: If True, commit and push changes after each migration (default: True)
            stop_on_failure: If True, stop on first failure; if False, continue (default: True)
        
        Returns:
            List of MigrationResult objects, one per migration
        
        Example:
            >>> runner = MigrationRunner(...)
            >>> migrations = [migration1, migration2, migration3]
            >>> results = await runner.run_migrations(migrations)
            >>> for result in results:
            ...     print(f"{result.migration.full_name}: {result.status}")
        """
        logger.info(f"Running batch of {len(migrations)} migrations")
        
        results = []
        
        for i, migration in enumerate(migrations, 1):
            logger.info(
                f"Processing migration {i}/{len(migrations)}: {migration.full_name}"
            )
            
            # Execute migration
            result = await self.run_migration(
                migration=migration,
                dry_run=dry_run,
                auto_commit=auto_commit,
                force=False  # Never force in batch mode
            )
            
            results.append(result)
            
            # Log result
            if result.status == MigrationStatus.COMPLETED:
                logger.info(
                    f"✓ Migration {migration.full_name} completed successfully "
                    f"({result.entities_created} entities, "
                    f"{result.relationships_created} relationships)"
                )
            elif result.status == MigrationStatus.SKIPPED:
                logger.info(f"⊘ Migration {migration.full_name} skipped (already applied)")
            elif result.status == MigrationStatus.FAILED:
                logger.error(f"✗ Migration {migration.full_name} failed: {result.error}")
                
                # Stop on failure if flag is set
                if stop_on_failure:
                    logger.error(
                        f"Stopping batch execution due to failure in "
                        f"{migration.full_name}"
                    )
                    break
        
        # Summary
        completed = sum(1 for r in results if r.status == MigrationStatus.COMPLETED)
        skipped = sum(1 for r in results if r.status == MigrationStatus.SKIPPED)
        failed = sum(1 for r in results if r.status == MigrationStatus.FAILED)
        
        logger.info(
            f"Batch execution complete: "
            f"{completed} completed, {skipped} skipped, {failed} failed"
        )
        
        return results
    
    def _get_changed_files(self) -> List[str]:
        """
        Get list of changed files in the Database Repository.
        
        Returns:
            List of file paths relative to the database repository root
        """
        db_repo_path = self.manager.db_repo_path
        
        try:
            # Get list of changed files (staged and unstaged)
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            changed_files = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Parse git status output
                # Format: "XY filename" where X is staged status, Y is unstaged status
                # We want all modified, added, or deleted files
                status = line[:2]
                filename = line[3:].strip()
                
                # Skip if no changes
                if status.strip() == '':
                    continue
                
                changed_files.append(filename)
            
            logger.debug(f"Found {len(changed_files)} changed files in database repository")
            return changed_files
        
        except subprocess.TimeoutExpired:
            logger.error("Git status query timed out after 30 seconds")
            return []
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Git status query failed: {e.stderr}")
            return []
        
        except Exception as e:
            logger.error(f"Unexpected error getting changed files: {e}")
            return []
    
    def _format_commit_message(
        self,
        migration: Migration,
        result: MigrationResult,
        batch_info: Optional[tuple] = None
    ) -> str:
        """
        Format Git commit message with migration metadata.
        
        Args:
            migration: Migration that was executed
            result: Result of migration execution
            batch_info: Optional tuple of (batch_number, total_batches) for batch commits
        
        Returns:
            Formatted commit message
        """
        # Get metadata from migration
        author = migration.author or "unknown"
        date = migration.date.strftime('%Y-%m-%d') if migration.date else "unknown"
        description = migration.description or "No description provided"
        
        # Build commit message
        title = f"Migration: {migration.full_name}"
        if batch_info:
            batch_num, total_batches = batch_info
            title += f" (Batch {batch_num}/{total_batches})"
        
        message_parts = [
            title,
            "",
            description,
            "",
            f"Author: {author}",
            f"Date: {date}",
            f"Entities created: {result.entities_created}",
            f"Relationships created: {result.relationships_created}",
            f"Duration: {result.duration_seconds:.1f}s"
        ]
        
        return "\n".join(message_parts)
    
    async def commit_and_push(
        self,
        migration: Migration,
        result: MigrationResult,
        dry_run: bool = False
    ) -> None:
        """
        Commit database changes and push to remote.
        
        This persists the data snapshot in the Database Repository,
        making the migration deterministic on subsequent runs.
        
        This method:
        - Gets list of changed files in the Database Repository
        - Determines if batch commits are needed (>1000 files)
        - Stages and commits changes with formatted commit message
        - Pushes commits to remote Database Repository
        - Handles errors gracefully
        
        Args:
            migration: Migration that was executed
            result: Result of migration execution
            dry_run: If True, don't actually commit or push (default: False)
        
        Raises:
            RuntimeError: If commit or push fails
        """
        if dry_run:
            logger.info("Dry run mode: skipping commit and push")
            return
        
        db_repo_path = self.manager.db_repo_path
        
        logger.info(f"Committing changes for migration {migration.full_name}")
        
        # Get list of changed files
        changed_files = self._get_changed_files()
        
        if len(changed_files) == 0:
            logger.info("No changes to commit")
            return
        
        logger.info(f"Found {len(changed_files)} changed files")
        
        # Determine if we need batch commits
        BATCH_COMMIT_THRESHOLD = 1000
        
        if len(changed_files) < BATCH_COMMIT_THRESHOLD:
            # Single commit for all files
            logger.info("Creating single commit for all changes")
            self._commit_all(migration, result, changed_files)
        else:
            # Batch commits
            logger.info(
                f"Creating batch commits ({len(changed_files)} files, "
                f"threshold: {BATCH_COMMIT_THRESHOLD})"
            )
            self._commit_in_batches(migration, result, changed_files)
        
        # Push to remote
        logger.info("Pushing commits to remote Database Repository")
        self._push_to_remote()
        
        # Clear the applied migrations cache so next check will see the new commit
        self.manager.clear_cache()
        
        logger.info(f"Successfully committed and pushed migration {migration.full_name}")
    
    def _commit_all(
        self,
        migration: Migration,
        result: MigrationResult,
        changed_files: List[str]
    ) -> None:
        """
        Commit all changed files in a single commit.
        
        Args:
            migration: Migration that was executed
            result: Result of migration execution
            changed_files: List of changed file paths
        
        Raises:
            RuntimeError: If commit fails
        """
        db_repo_path = self.manager.db_repo_path
        
        try:
            # Stage all changed files
            logger.debug(f"Staging {len(changed_files)} files")
            subprocess.run(
                ["git", "add", "-A"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minutes for staging
            )
            
            # Format commit message
            commit_message = self._format_commit_message(migration, result)
            
            # Create commit
            logger.debug("Creating Git commit")
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minutes for commit
            )
            
            logger.info(f"Created commit for {len(changed_files)} files")
        
        except subprocess.TimeoutExpired as e:
            error_msg = f"Git operation timed out: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except subprocess.CalledProcessError as e:
            error_msg = f"Git commit failed: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during commit: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _commit_in_batches(
        self,
        migration: Migration,
        result: MigrationResult,
        changed_files: List[str]
    ) -> None:
        """
        Commit changed files in batches to avoid huge commits.
        
        Args:
            migration: Migration that was executed
            result: Result of migration execution
            changed_files: List of changed file paths
        
        Raises:
            RuntimeError: If any commit fails
        """
        db_repo_path = self.manager.db_repo_path
        BATCH_SIZE = 1000
        
        # Calculate number of batches
        total_batches = (len(changed_files) + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(
            f"Committing {len(changed_files)} files in {total_batches} batches "
            f"of {BATCH_SIZE} files each"
        )
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(changed_files))
            batch_files = changed_files[start_idx:end_idx]
            
            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch_files)} files)"
            )
            
            try:
                # Stage files in this batch
                logger.debug(f"Staging {len(batch_files)} files for batch {batch_num}")
                
                # Stage files one by one to avoid command line length limits
                for file_path in batch_files:
                    subprocess.run(
                        ["git", "add", file_path],
                        cwd=db_repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10
                    )
                
                # Format commit message with batch info
                commit_message = self._format_commit_message(
                    migration,
                    result,
                    batch_info=(batch_num, total_batches)
                )
                
                # Create commit for this batch
                logger.debug(f"Creating Git commit for batch {batch_num}")
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=db_repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300  # 5 minutes for commit
                )
                
                logger.info(
                    f"Created commit for batch {batch_num}/{total_batches} "
                    f"({len(batch_files)} files)"
                )
            
            except subprocess.TimeoutExpired as e:
                error_msg = f"Git operation timed out on batch {batch_num}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            except subprocess.CalledProcessError as e:
                error_msg = f"Git commit failed on batch {batch_num}: {e.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            except Exception as e:
                error_msg = f"Unexpected error on batch {batch_num}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        logger.info(f"Successfully created {total_batches} batch commits")
    
    def _push_to_remote(self) -> None:
        """
        Push commits to remote Database Repository.
        
        If no remote is configured, logs a warning and skips the push.
        This is common in test environments or local-only repositories.
        
        Raises:
            RuntimeError: If push fails (but not if no remote is configured)
        """
        db_repo_path = self.manager.db_repo_path
        
        try:
            # Check if a remote is configured
            remote_check = subprocess.run(
                ["git", "remote"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            if not remote_check.stdout.strip():
                logger.warning(
                    "No Git remote configured in Database Repository. "
                    "Skipping push. Changes are committed locally."
                )
                return
            
            logger.debug("Pushing commits to remote")
            
            # Push with a generous timeout for large pushes
            result = subprocess.run(
                ["git", "push"],
                cwd=db_repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=1800  # 30 minutes for push
            )
            
            logger.info("Successfully pushed commits to remote")
            
            # Log push output if any
            if result.stdout:
                logger.debug(f"Push output: {result.stdout}")
        
        except subprocess.TimeoutExpired as e:
            error_msg = f"Git push timed out after 30 minutes: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except subprocess.CalledProcessError as e:
            # Check if error is about no remote configured
            if "No configured push destination" in e.stderr or "no upstream branch" in e.stderr:
                logger.warning(
                    "No Git remote configured or no upstream branch set. "
                    "Skipping push. Changes are committed locally."
                )
                return
            
            error_msg = f"Git push failed: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during push: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
