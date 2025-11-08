"""
Migration service for managing database evolution through versioned migration folders.

This package provides infrastructure for discovering, validating, and executing
migrations that update the Nepal Entity Service database.
"""

from nes2.services.migration.context import MigrationContext
from nes2.services.migration.manager import MigrationManager
from nes2.services.migration.models import (
    Migration,
    MigrationResult,
    MigrationStatus,
)
from nes2.services.migration.validation import (
    ValidationResult,
    validate_migration,
    validate_migration_metadata,
    validate_migration_naming,
    validate_migration_structure,
)

__all__ = [
    "Migration",
    "MigrationContext",
    "MigrationManager",
    "MigrationResult",
    "MigrationStatus",
    "ValidationResult",
    "validate_migration",
    "validate_migration_metadata",
    "validate_migration_naming",
    "validate_migration_structure",
]
