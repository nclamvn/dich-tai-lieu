"""
Memory Store for Author Engine (Phase 4.3)

Structured memory tracking for:
- Characters (names, descriptions, relationships, arcs)
- Timeline (events, chronology, consistency)
- Plot points (themes, motifs, major events)
- World building (locations, rules, lore)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Set
from pathlib import Path
import json
from enum import Enum


class EntityType(str, Enum):
    """Types of entities to track"""
    CHARACTER = "character"
    LOCATION = "location"
    EVENT = "event"
    THEME = "theme"
    OBJECT = "object"


@dataclass
class Character:
    """Character information and development"""
    name: str
    aliases: List[str] = field(default_factory=list)  # Alternative names
    description: str = ""
    role: str = ""  # protagonist, antagonist, supporting, etc.

    # Attributes
    traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # name -> relationship

    # Development tracking
    first_appearance_chapter: Optional[int] = None
    last_appearance_chapter: Optional[int] = None
    character_arc: str = ""

    # Consistency tracking
    mentioned_attributes: Dict[str, List[str]] = field(default_factory=dict)  # attr -> [values]

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_alias(self, alias: str):
        """Add alternative name"""
        if alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = datetime.now()

    def add_trait(self, trait: str):
        """Add character trait"""
        if trait not in self.traits:
            self.traits.append(trait)
            self.updated_at = datetime.now()

    def add_relationship(self, character_name: str, relationship: str):
        """Add or update relationship"""
        self.relationships[character_name] = relationship
        self.updated_at = datetime.now()

    def record_attribute(self, attr_name: str, value: str):
        """Record an attribute mention for consistency checking"""
        if attr_name not in self.mentioned_attributes:
            self.mentioned_attributes[attr_name] = []

        if value not in self.mentioned_attributes[attr_name]:
            self.mentioned_attributes[attr_name].append(value)
            self.updated_at = datetime.now()

    def check_consistency(self) -> List[str]:
        """Check for attribute inconsistencies"""
        inconsistencies = []

        for attr, values in self.mentioned_attributes.items():
            if len(values) > 1:
                inconsistencies.append(
                    f"{self.name}'s {attr} has conflicting values: {', '.join(values)}"
                )

        return inconsistencies


@dataclass
class TimelineEvent:
    """A significant event in the story timeline"""
    event_id: str
    description: str
    chapter: int
    timestamp: Optional[str] = None  # Story time (e.g., "Day 3", "Chapter 5")
    participants: List[str] = field(default_factory=list)  # Character names
    location: Optional[str] = None
    significance: str = ""  # Why this event matters
    consequences: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PlotPoint:
    """Major plot point or theme"""
    point_id: str
    type: str  # "theme", "motif", "conflict", "revelation", etc.
    description: str
    first_introduced_chapter: int
    development: List[Dict[str, str]] = field(default_factory=list)  # chapter -> how it develops
    resolution_chapter: Optional[int] = None
    status: str = "active"  # active, resolved, abandoned

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorldElement:
    """World building element (locations, rules, lore)"""
    element_id: str
    type: str  # "location", "rule", "lore", "magic_system", etc.
    name: str
    description: str
    first_mentioned_chapter: int
    properties: Dict[str, str] = field(default_factory=dict)
    consistency_notes: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class MemoryStore:
    """
    Structured memory store for author projects

    Tracks characters, timeline, plot points, and world building
    to ensure consistency across chapters.
    """

    def __init__(self, project_path: Path):
        """
        Initialize memory store for a project

        Args:
            project_path: Path to project directory
        """
        self.project_path = project_path
        self.memory_path = project_path / "memory"
        self.memory_path.mkdir(parents=True, exist_ok=True)

        # Memory databases
        self.characters: Dict[str, Character] = {}
        self.timeline: List[TimelineEvent] = []
        self.plot_points: Dict[str, PlotPoint] = {}
        self.world_elements: Dict[str, WorldElement] = {}

        # Load existing memory
        self.load()

    # =========================================================================
    # CHARACTER MANAGEMENT
    # =========================================================================

    def add_character(self, character: Character) -> None:
        """Add or update character"""
        self.characters[character.name] = character
        self.save()

    def get_character(self, name: str) -> Optional[Character]:
        """Get character by name or alias"""
        # Direct match
        if name in self.characters:
            return self.characters[name]

        # Check aliases
        for char in self.characters.values():
            if name in char.aliases:
                return char

        return None

    def list_characters(self, chapter: Optional[int] = None) -> List[Character]:
        """List all characters, optionally filtered by chapter appearance"""
        if chapter is None:
            return list(self.characters.values())

        return [
            char for char in self.characters.values()
            if (char.first_appearance_chapter is not None and
                char.first_appearance_chapter <= chapter and
                (char.last_appearance_chapter is None or
                 char.last_appearance_chapter >= chapter))
        ]

    def check_character_consistency(self) -> Dict[str, List[str]]:
        """Check all characters for inconsistencies"""
        issues = {}

        for name, char in self.characters.items():
            inconsistencies = char.check_consistency()
            if inconsistencies:
                issues[name] = inconsistencies

        return issues

    # =========================================================================
    # TIMELINE MANAGEMENT
    # =========================================================================

    def add_event(self, event: TimelineEvent) -> None:
        """Add event to timeline"""
        self.timeline.append(event)
        # Sort by chapter
        self.timeline.sort(key=lambda e: e.chapter)
        self.save()

    def get_events(
        self,
        chapter: Optional[int] = None,
        participant: Optional[str] = None
    ) -> List[TimelineEvent]:
        """Get events, optionally filtered"""
        events = self.timeline

        if chapter is not None:
            events = [e for e in events if e.chapter == chapter]

        if participant is not None:
            events = [e for e in events if participant in e.participants]

        return events

    def get_timeline_summary(self, up_to_chapter: int) -> str:
        """Get summary of events up to a chapter"""
        events = [e for e in self.timeline if e.chapter <= up_to_chapter]

        if not events:
            return "No significant events recorded yet."

        summary_lines = ["Timeline of Events:"]
        for event in events:
            summary_lines.append(
                f"- Chapter {event.chapter}: {event.description}"
            )

        return "\n".join(summary_lines)

    # =========================================================================
    # PLOT POINT MANAGEMENT
    # =========================================================================

    def add_plot_point(self, plot_point: PlotPoint) -> None:
        """Add or update plot point"""
        self.plot_points[plot_point.point_id] = plot_point
        self.save()

    def get_plot_point(self, point_id: str) -> Optional[PlotPoint]:
        """Get plot point by ID"""
        return self.plot_points.get(point_id)

    def list_active_plot_points(self) -> List[PlotPoint]:
        """List all active (unresolved) plot points"""
        return [p for p in self.plot_points.values() if p.status == "active"]

    def get_plot_summary(self) -> str:
        """Get summary of major plot points"""
        if not self.plot_points:
            return "No plot points tracked yet."

        summary_lines = ["Major Plot Points:"]

        for point in self.plot_points.values():
            status_indicator = "✓" if point.status == "resolved" else "•"
            summary_lines.append(
                f"{status_indicator} {point.type.title()}: {point.description} "
                f"(Ch. {point.first_introduced_chapter})"
            )

        return "\n".join(summary_lines)

    # =========================================================================
    # WORLD BUILDING MANAGEMENT
    # =========================================================================

    def add_world_element(self, element: WorldElement) -> None:
        """Add or update world building element"""
        self.world_elements[element.element_id] = element
        self.save()

    def get_world_element(self, element_id: str) -> Optional[WorldElement]:
        """Get world element by ID"""
        return self.world_elements.get(element_id)

    def list_world_elements(self, element_type: Optional[str] = None) -> List[WorldElement]:
        """List world elements, optionally filtered by type"""
        elements = list(self.world_elements.values())

        if element_type:
            elements = [e for e in elements if e.type == element_type]

        return elements

    # =========================================================================
    # CONTEXT RETRIEVAL
    # =========================================================================

    def get_context_for_chapter(self, chapter: int) -> str:
        """
        Get relevant context for writing a chapter

        Returns formatted context including:
        - Active characters
        - Recent events
        - Active plot points
        - Relevant world elements
        """
        context_parts = []

        # Characters
        active_chars = self.list_characters(chapter)
        if active_chars:
            char_names = [c.name for c in active_chars[:10]]  # Limit to top 10
            context_parts.append(f"Active Characters: {', '.join(char_names)}")

        # Recent events (last 3 chapters)
        recent_events = [
            e for e in self.timeline
            if e.chapter >= chapter - 3 and e.chapter < chapter
        ]
        if recent_events:
            context_parts.append("\nRecent Events:")
            for event in recent_events[-5:]:  # Last 5 events
                context_parts.append(f"- Ch.{event.chapter}: {event.description}")

        # Active plot points
        active_plots = self.list_active_plot_points()
        if active_plots:
            context_parts.append("\nActive Plot Threads:")
            for point in active_plots[:5]:  # Top 5
                context_parts.append(f"- {point.description}")

        return "\n".join(context_parts) if context_parts else "No context available yet."

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save(self) -> None:
        """Save all memory to disk"""
        # Save characters
        chars_data = {
            name: {
                **asdict(char),
                'created_at': char.created_at.isoformat(),
                'updated_at': char.updated_at.isoformat()
            }
            for name, char in self.characters.items()
        }

        with open(self.memory_path / "characters.json", "w", encoding="utf-8") as f:
            json.dump(chars_data, f, indent=2, ensure_ascii=False)

        # Save timeline
        timeline_data = [
            {
                **asdict(event),
                'created_at': event.created_at.isoformat()
            }
            for event in self.timeline
        ]

        with open(self.memory_path / "timeline.json", "w", encoding="utf-8") as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)

        # Save plot points
        plots_data = {
            pid: {
                **asdict(point),
                'created_at': point.created_at.isoformat(),
                'updated_at': point.updated_at.isoformat()
            }
            for pid, point in self.plot_points.items()
        }

        with open(self.memory_path / "plot_points.json", "w", encoding="utf-8") as f:
            json.dump(plots_data, f, indent=2, ensure_ascii=False)

        # Save world elements
        world_data = {
            eid: {
                **asdict(elem),
                'created_at': elem.created_at.isoformat(),
                'updated_at': elem.updated_at.isoformat()
            }
            for eid, elem in self.world_elements.items()
        }

        with open(self.memory_path / "world.json", "w", encoding="utf-8") as f:
            json.dump(world_data, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load memory from disk"""
        # Load characters
        chars_file = self.memory_path / "characters.json"
        if chars_file.exists():
            with open(chars_file, "r", encoding="utf-8") as f:
                chars_data = json.load(f)

            for name, data in chars_data.items():
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                self.characters[name] = Character(**data)

        # Load timeline
        timeline_file = self.memory_path / "timeline.json"
        if timeline_file.exists():
            with open(timeline_file, "r", encoding="utf-8") as f:
                timeline_data = json.load(f)

            for data in timeline_data:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                self.timeline.append(TimelineEvent(**data))

        # Load plot points
        plots_file = self.memory_path / "plot_points.json"
        if plots_file.exists():
            with open(plots_file, "r", encoding="utf-8") as f:
                plots_data = json.load(f)

            for pid, data in plots_data.items():
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                self.plot_points[pid] = PlotPoint(**data)

        # Load world elements
        world_file = self.memory_path / "world.json"
        if world_file.exists():
            with open(world_file, "r", encoding="utf-8") as f:
                world_data = json.load(f)

            for eid, data in world_data.items():
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                self.world_elements[eid] = WorldElement(**data)
