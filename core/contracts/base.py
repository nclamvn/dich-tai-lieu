#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Contract Classes

Defines the foundation for all agent contracts.
Contracts are immutable, serializable, and validatable.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, TypeVar
from datetime import datetime
import json
import hashlib


T = TypeVar('T')


class ContractError(Exception):
    """Base error for contract violations"""
    pass


class ContractValidationError(ContractError):
    """Raised when contract validation fails"""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Contract validation failed: {errors}")


@dataclass
class ContractMetadata:
    """Metadata for all contracts"""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_agent: str = ""
    target_agent: str = ""
    checksum: str = ""

    def calculate_checksum(self, data: Dict) -> str:
        """Calculate checksum for contract data"""
        # Remove checksum field before calculating
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        if "metadata" in data_copy and isinstance(data_copy["metadata"], dict):
            data_copy["metadata"] = {k: v for k, v in data_copy["metadata"].items() if k != "checksum"}
        json_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractMetadata':
        """Create from dictionary"""
        return cls(
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", ""),
            source_agent=data.get("source_agent", ""),
            target_agent=data.get("target_agent", ""),
            checksum=data.get("checksum", ""),
        )


class BaseContract(ABC):
    """
    Abstract base class for all agent contracts.

    All contracts must:
    1. Be serializable to JSON
    2. Be deserializable from JSON
    3. Be validatable
    4. Have metadata
    """

    @property
    @abstractmethod
    def metadata(self) -> ContractMetadata:
        """Contract metadata"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert contract to dictionary"""
        pass

    @abstractmethod
    def to_json(self, indent: int = 2) -> str:
        """Convert contract to JSON string"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseContract':
        """Create contract from dictionary"""
        pass

    @classmethod
    def from_json(cls, json_str: str) -> 'BaseContract':
        """Create contract from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate contract.
        Returns list of validation errors (empty if valid).
        """
        pass

    def is_valid(self) -> bool:
        """Check if contract is valid"""
        return len(self.validate()) == 0

    def assert_valid(self) -> None:
        """Raise error if contract is invalid"""
        errors = self.validate()
        if errors:
            raise ContractValidationError(errors)

    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(source={self.metadata.source_agent}, target={self.metadata.target_agent})>"
