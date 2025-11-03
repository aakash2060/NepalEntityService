"""Validation functions for identifiers."""

import re

from ..constraints import (ENTITY_SUBTYPE_PATTERN, ENTITY_TYPE_PATTERN,
                           MAX_SLUG_LENGTH, MAX_SUBTYPE_LENGTH,
                           MAX_TYPE_LENGTH, MIN_SLUG_LENGTH, SLUG_PATTERN)
from .builders import (break_actor_id, break_entity_id, break_relationship_id,
                       break_version_id)


def is_valid_entity_id(entity_id: str) -> bool:
    """Validate if a string is a valid entity ID format.

    Args:
        entity_id: The entity ID string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_entity_id(entity_id)
        return True
    except ValueError:
        return False


def validate_entity_id(entity_id: str) -> str:
    """Validate entity ID and return it if valid, raise ValueError if not.

    Validates against the same rules as the Entity model:
    - Type must match ENTITY_TYPE_PATTERN and length constraints
    - Subtype (if present) must match ENTITY_SUBTYPE_PATTERN and length constraints
    - Slug must match SLUG_PATTERN and length constraints

    Args:
        entity_id: The entity ID string to validate

    Returns:
        The validated entity ID

    Raises:
        ValueError: If the entity ID format is invalid
    """
    try:
        components = break_entity_id(entity_id)
    except ValueError as e:
        raise ValueError(f"Invalid entity ID format: {entity_id}") from e

    # Validate type
    if len(components.type) > MAX_TYPE_LENGTH:
        raise ValueError(f"Entity type too long: {components.type}")
    if not re.match(ENTITY_TYPE_PATTERN, components.type):
        raise ValueError(f"Invalid entity type format: {components.type}")

    # Validate subtype if present
    if components.subtype is not None:
        if len(components.subtype) > MAX_SUBTYPE_LENGTH:
            raise ValueError(f"Entity subtype too long: {components.subtype}")
        if not re.match(ENTITY_SUBTYPE_PATTERN, components.subtype):
            raise ValueError(f"Invalid entity subtype format: {components.subtype}")

    # Validate slug
    if len(components.slug) < MIN_SLUG_LENGTH or len(components.slug) > MAX_SLUG_LENGTH:
        raise ValueError(f"Entity slug length invalid: {components.slug}")
    if not re.match(SLUG_PATTERN, components.slug):
        raise ValueError(f"Invalid entity slug format: {components.slug}")

    return entity_id


def is_valid_relationship_id(relationship_id: str) -> bool:
    """Validate if a string is a valid relationship ID format."""
    try:
        validate_relationship_id(relationship_id)
        return True
    except ValueError:
        return False


def validate_relationship_id(relationship_id: str) -> str:
    """Validate relationship ID and return it if valid, raise ValueError if not."""
    try:
        components = break_relationship_id(relationship_id)
    except ValueError as e:
        raise ValueError(f"Invalid relationship ID format: {relationship_id}") from e

    # Validate that source and target are valid entity IDs
    validate_entity_id(components.source)
    validate_entity_id(components.target)

    return relationship_id


def is_valid_version_id(version_id: str) -> bool:
    """Validate if a string is a valid version ID format."""
    try:
        validate_version_id(version_id)
        return True
    except ValueError:
        return False


def validate_version_id(version_id: str) -> str:
    """Validate version ID and return it if valid, raise ValueError if not."""
    try:
        components = break_version_id(version_id)
    except ValueError as e:
        # Re-raise the original error to preserve specific error messages
        raise e

    # Validate the underlying entity or relationship ID
    if components.entity_or_relationship_id.startswith("entity:"):
        validate_entity_id(components.entity_or_relationship_id)
    elif components.entity_or_relationship_id.startswith("relationship:"):
        validate_relationship_id(components.entity_or_relationship_id)

    return version_id


def is_valid_actor_id(actor_id: str) -> bool:
    """Validate if a string is a valid actor ID format."""
    try:
        validate_actor_id(actor_id)
        return True
    except ValueError:
        return False


def validate_actor_id(actor_id: str) -> str:
    """Validate actor ID and return it if valid, raise ValueError if not."""
    try:
        components = break_actor_id(actor_id)
    except ValueError as e:
        raise ValueError(f"Invalid actor ID format: {actor_id}") from e

    # Validate slug follows same pattern as entity slugs
    if len(components.slug) < MIN_SLUG_LENGTH or len(components.slug) > MAX_SLUG_LENGTH:
        raise ValueError(f"Actor slug length invalid: {components.slug}")
    if not re.match(SLUG_PATTERN, components.slug):
        raise ValueError(f"Invalid actor slug format: {components.slug}")

    return actor_id
