"""
Migration: 000-example-migration
Description: Create initial example entity - BP Koirala
Author: system@nepalentity.org
Date: 2024-11-08
"""

from nes2.models.entity import Entity, EntityType, Name, NameKind, NameParts

# Migration metadata (used for Git commit message)
AUTHOR = "system@nepalentity.org"
DATE = "2024-11-08"
DESCRIPTION = "Create initial example entity - BP Koirala"


async def migrate(context):
    """
    Create the first entity in the database - BP Koirala.
    
    This migration creates a person entity for Bishweshwar Prasad Koirala,
    the first democratically elected Prime Minister of Nepal.
    
    Args:
        context: MigrationContext with access to services and data
    """
    context.log("Starting migration: Creating BP Koirala entity")
    
    # Create actor for this migration
    actor_id = "actor:migration:000-example-migration"
    
    # Create BP Koirala entity
    bp_koirala = Entity(
        slug="bishweshwar-prasad-koirala",
        type=EntityType.PERSON,
        names=[
            Name(
                kind=NameKind.PRIMARY,
                ne=NameParts(full="विश्वेश्वर प्रसाद कोइराला"),
                en=NameParts(
                    full="Bishweshwar Prasad Koirala",
                    given="Bishweshwar Prasad",
                    family="Koirala"
                )
            ),
            Name(
                kind=NameKind.COMMON,
                ne=NameParts(full="बी पी कोइराला"),
                en=NameParts(full="BP Koirala")
            )
        ]
    )
    
    # Create the entity using the publication service
    created_entity = await context.create_entity(
        entity=bp_koirala,
        actor_id=actor_id,
        change_description="Initial migration: Create BP Koirala entity"
    )
    
    context.log(f"Created entity: {created_entity.slug}")
    context.log("Migration completed successfully")
