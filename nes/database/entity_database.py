"""Abstract EntityDatabase class for CRUD operations."""

from abc import ABC, abstractmethod
from typing import List, Optional

from nes.core.models.entity import Entity, EntityType
from nes.core.models.relationship import Relationship
from nes.core.models.version import Actor, Version


class EntityDatabase(ABC):
    """Abstract base class for entity database operations."""

    @abstractmethod
    async def put_entity(self, entity: Entity) -> Entity:
        pass

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        pass

    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        pass

    @abstractmethod
    async def list_entities(
        self,
        limit: int = 100,
        offset: int = 0,
        type: Optional[EntityType] = None,
        subtype: Optional[str] = None,
    ) -> List[Entity]:
        pass

    @abstractmethod
    async def put_relationship(self, relationship: Relationship) -> Relationship:
        pass

    @abstractmethod
    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        pass

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        pass

    @abstractmethod
    async def list_relationships(
        self, limit: int = 100, offset: int = 0
    ) -> List[Relationship]:
        pass

    @abstractmethod
    async def put_version(self, version: Version) -> Version:
        pass

    @abstractmethod
    async def get_version(self, version_id: str) -> Optional[Version]:
        pass

    @abstractmethod
    async def delete_version(self, version_id: str) -> bool:
        pass

    @abstractmethod
    async def list_versions(self, limit: int = 100, offset: int = 0) -> List[Version]:
        """List versions.

        TODO: This method should be changed to require an entity_id or relationship_id
        parameter to list versions for a specific entity or relationship.
        """
        pass

    @abstractmethod
    async def put_actor(self, actor: Actor) -> Actor:
        pass

    @abstractmethod
    async def get_actor(self, actor_id: str) -> Optional[Actor]:
        pass

    @abstractmethod
    async def delete_actor(self, actor_id: str) -> bool:
        pass

    @abstractmethod
    async def list_actors(self, limit: int = 100, offset: int = 0) -> List[Actor]:
        pass
