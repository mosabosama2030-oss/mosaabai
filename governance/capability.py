"""Capability model — immutable named permissions with constraints."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Mapping


@dataclass(frozen=True)
class Capability:
    name: str
    constraints: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "constraints", MappingProxyType(dict(self.constraints))
        )

    def __hash__(self) -> int:
        items = tuple(sorted((str(k), repr(v)) for k, v in self.constraints.items()))
        return hash((self.name, items))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "constraints": dict(sorted(self.constraints.items())),
        }


class CapabilitySet:
    """Frozenset wrapper over Capability with subset operations."""

    def __init__(self, items: Iterable[Capability] = ()) -> None:
        self._data: frozenset[Capability] = frozenset(items)

    def __contains__(self, item: object) -> bool:
        return item in self._data

    def __iter__(self) -> Iterator[Capability]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def issubset(self, other: CapabilitySet) -> bool:
        return self._data.issubset(other._data)

    def issuperset(self, other: CapabilitySet) -> bool:
        return self._data.issuperset(other._data)

    def names(self) -> frozenset[str]:
        return frozenset(c.name for c in self._data)
