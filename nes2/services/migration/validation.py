"""
Validation functions for migration folders and scripts.

This module provides functions to validate:
- Migration folder structure (has migrate.py, README.md)
- Migration naming conventions (NNN-descriptive-name)
- Migration metadata (AUTHOR, DATE, DESCRIPTION)
"""

import ast
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ValidationResult:
    """Result of a validation check."""
    
    is_valid: bool
    """Whether the validation passed."""
    
    errors: List[str]
    """List of validation error messages."""
    
    warnings: List[str]
    """List of validation warning messages."""
    
    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context."""
        return self.is_valid
    
    def __str__(self) -> str:
        """String representation of validation result."""
        if self.is_valid:
            msg = "Validation passed"
            if self.warnings:
                msg += f" with {len(self.warnings)} warning(s)"
            return msg
        else:
            return f"Validation failed with {len(self.errors)} error(s)"


def validate_migration_naming(folder_name: str) -> ValidationResult:
    """
    Validate migration folder naming convention.
    
    Migration folders must follow the pattern: NNN-descriptive-name
    where NNN is a 3-digit numeric prefix (000-999).
    
    Args:
        folder_name: Name of the migration folder (not full path)
    
    Returns:
        ValidationResult indicating whether the name is valid
    
    Examples:
        >>> validate_migration_naming("000-initial-locations")
        ValidationResult(is_valid=True, errors=[], warnings=[])
        
        >>> validate_migration_naming("invalid-name")
        ValidationResult(is_valid=False, errors=['...'], warnings=[])
    """
    errors = []
    warnings = []
    
    # Pattern: NNN-descriptive-name
    pattern = r'^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)$'
    match = re.match(pattern, folder_name)
    
    if not match:
        errors.append(
            f"Migration folder name '{folder_name}' does not match required pattern: "
            "NNN-descriptive-name (e.g., '000-initial-locations')"
        )
        
        # Provide specific guidance
        if not folder_name[0:3].isdigit():
            errors.append("Migration name must start with a 3-digit numeric prefix (000-999)")
        
        if '-' not in folder_name:
            errors.append("Migration name must contain a hyphen after the numeric prefix")
        
        # Check for invalid characters
        if re.search(r'[A-Z]', folder_name):
            warnings.append("Migration name should use lowercase letters only")
        
        if re.search(r'[_\s]', folder_name):
            errors.append("Migration name should use hyphens, not underscores or spaces")
    
    else:
        prefix_str, name = match.groups()
        prefix = int(prefix_str)
        
        # Validate prefix range
        if prefix > 999:
            errors.append(f"Migration prefix {prefix} exceeds maximum value of 999")
        
        # Validate descriptive name
        if len(name) < 3:
            warnings.append(
                f"Migration name '{name}' is very short. "
                "Consider using a more descriptive name."
            )
        
        if len(name) > 50:
            warnings.append(
                f"Migration name '{name}' is very long ({len(name)} characters). "
                "Consider using a shorter, more concise name."
            )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_migration_structure(folder_path: Path) -> ValidationResult:
    """
    Validate migration folder structure.
    
    A valid migration folder must contain:
    - migrate.py or run.py (required): Main migration script
    - README.md (required): Documentation
    
    Args:
        folder_path: Path to the migration folder
    
    Returns:
        ValidationResult indicating whether the structure is valid
    """
    errors = []
    warnings = []
    
    if not folder_path.exists():
        errors.append(f"Migration folder does not exist: {folder_path}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    if not folder_path.is_dir():
        errors.append(f"Migration path is not a directory: {folder_path}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    # Check for main script file
    migrate_py = folder_path / "migrate.py"
    run_py = folder_path / "run.py"
    
    if not migrate_py.exists() and not run_py.exists():
        errors.append(
            "Migration folder must contain either 'migrate.py' or 'run.py' script"
        )
    elif migrate_py.exists() and run_py.exists():
        warnings.append(
            "Migration folder contains both 'migrate.py' and 'run.py'. "
            "Only 'migrate.py' will be used."
        )
    
    # Check for README
    readme_md = folder_path / "README.md"
    if not readme_md.exists():
        errors.append("Migration folder must contain 'README.md' documentation")
    
    # Check for common issues
    if (folder_path / "__pycache__").exists():
        warnings.append(
            "Migration folder contains __pycache__ directory. "
            "Consider adding it to .gitignore."
        )
    
    # List files for informational purposes
    files = list(folder_path.iterdir())
    if len(files) == 0:
        errors.append("Migration folder is empty")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_migration_metadata(script_path: Path) -> ValidationResult:
    """
    Validate migration script metadata.
    
    Migration scripts must define the following module-level constants:
    - AUTHOR (str): Email or name of the migration author
    - DATE (str): Date in YYYY-MM-DD format
    - DESCRIPTION (str): Brief description of what the migration does
    
    Args:
        script_path: Path to the migration script (migrate.py or run.py)
    
    Returns:
        ValidationResult indicating whether the metadata is valid
    """
    errors = []
    warnings = []
    
    if not script_path.exists():
        errors.append(f"Migration script does not exist: {script_path}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    try:
        # Parse the script as AST to extract metadata
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(script_path))
        
        # Extract module-level assignments
        metadata = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id in ['AUTHOR', 'DATE', 'DESCRIPTION']:
                            # Extract the value
                            if isinstance(node.value, ast.Constant):
                                metadata[target.id] = node.value.value
                            elif isinstance(node.value, ast.Str):  # Python 3.7 compatibility
                                metadata[target.id] = node.value.s
        
        # Validate required metadata
        required_fields = ['AUTHOR', 'DATE', 'DESCRIPTION']
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Migration script must define {field} constant")
            elif not metadata[field] or not isinstance(metadata[field], str):
                errors.append(f"{field} must be a non-empty string")
            elif metadata[field].strip() == "" or metadata[field].startswith("[TODO"):
                errors.append(
                    f"{field} contains placeholder text. "
                    "Please provide actual metadata."
                )
        
        # Validate AUTHOR format
        if 'AUTHOR' in metadata:
            author = metadata['AUTHOR']
            if '@' in author:
                # Looks like an email, validate basic format
                if not re.match(r'^[^@]+@[^@]+\.[^@]+$', author):
                    warnings.append(
                        f"AUTHOR '{author}' looks like an email but format is invalid"
                    )
            elif len(author) < 3:
                warnings.append(
                    f"AUTHOR '{author}' is very short. "
                    "Consider using full name or email."
                )
        
        # Validate DATE format
        if 'DATE' in metadata:
            date_str = metadata['DATE']
            try:
                # Try to parse as YYYY-MM-DD
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                errors.append(
                    f"DATE '{date_str}' is not in YYYY-MM-DD format "
                    "(e.g., '2024-01-20')"
                )
        
        # Validate DESCRIPTION
        if 'DESCRIPTION' in metadata:
            description = metadata['DESCRIPTION']
            if len(description) < 10:
                warnings.append(
                    "DESCRIPTION is very short. "
                    "Consider providing more detail about what the migration does."
                )
            elif len(description) > 200:
                warnings.append(
                    "DESCRIPTION is very long. "
                    "Consider moving detailed information to README.md."
                )
        
        # Check for migrate() function
        has_migrate_function = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == 'migrate':
                    has_migrate_function = True
                    
                    # Check if it's async
                    if not isinstance(node, ast.AsyncFunctionDef):
                        warnings.append(
                            "migrate() function should be async (async def migrate)"
                        )
                    
                    # Check parameters
                    if len(node.args.args) != 1:
                        errors.append(
                            "migrate() function must accept exactly one parameter (context)"
                        )
                    break
        
        if not has_migrate_function:
            errors.append(
                "Migration script must define a migrate() function "
                "(async def migrate(context))"
            )
    
    except SyntaxError as e:
        errors.append(f"Migration script has syntax error: {e}")
    except Exception as e:
        errors.append(f"Failed to parse migration script: {e}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_migration(folder_path: Path) -> ValidationResult:
    """
    Perform complete validation of a migration folder.
    
    This combines all validation checks:
    - Naming convention
    - Folder structure
    - Script metadata
    
    Args:
        folder_path: Path to the migration folder
    
    Returns:
        Combined ValidationResult from all checks
    """
    all_errors = []
    all_warnings = []
    
    # Validate naming
    folder_name = folder_path.name
    naming_result = validate_migration_naming(folder_name)
    all_errors.extend(naming_result.errors)
    all_warnings.extend(naming_result.warnings)
    
    # Validate structure
    structure_result = validate_migration_structure(folder_path)
    all_errors.extend(structure_result.errors)
    all_warnings.extend(structure_result.warnings)
    
    # Validate metadata (if script exists)
    script_path = folder_path / "migrate.py"
    if not script_path.exists():
        script_path = folder_path / "run.py"
    
    if script_path.exists():
        metadata_result = validate_migration_metadata(script_path)
        all_errors.extend(metadata_result.errors)
        all_warnings.extend(metadata_result.warnings)
    
    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )
