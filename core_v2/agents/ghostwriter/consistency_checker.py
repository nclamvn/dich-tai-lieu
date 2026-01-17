"""
Consistency Checker for Author Engine (Phase 5C)

Automatically detects inconsistencies in:
- Character attributes (physical descriptions, traits)
- Timeline (event ordering, temporal logic)
- Plot threads (unresolved storylines, abandoned plots)
- World building (location properties, rules)

Phase 5C: Enhanced with LLM semantic checking for deeper analysis
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
from datetime import datetime
from pathlib import Path
from enum import Enum
import json
import asyncio

from config.logging_config import get_logger
logger = get_logger(__name__)

from .memory_store import MemoryStore, Character, TimelineEvent, PlotPoint, WorldElement
from . import llm_prompts


class SeverityLevel(str, Enum):
    """Severity levels for consistency issues"""
    CRITICAL = "critical"  # Major plot hole or contradiction
    WARNING = "warning"   # Potential issue that should be reviewed
    INFO = "info"        # Minor inconsistency or suggestion


class IssueType(str, Enum):
    """Types of consistency issues"""
    CHARACTER_ATTRIBUTE = "character_attribute"
    CHARACTER_PRESENCE = "character_presence"
    TIMELINE_ORDER = "timeline_order"
    TIMELINE_GAP = "timeline_gap"
    PLOT_UNRESOLVED = "plot_unresolved"
    PLOT_ABANDONED = "plot_abandoned"
    WORLD_CONTRADICTION = "world_contradiction"


@dataclass
class ConsistencyIssue:
    """Represents a detected consistency issue"""
    issue_id: str
    issue_type: IssueType
    severity: SeverityLevel
    title: str
    description: str

    # Location information
    chapters_affected: List[int] = field(default_factory=list)
    entities_affected: List[str] = field(default_factory=list)

    # Details
    conflicting_values: Dict[str, str] = field(default_factory=dict)
    suggestion: Optional[str] = None

    # Metadata
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class ConsistencyReport:
    """Complete consistency check report"""
    project_id: str
    author_id: str

    # Issues by severity
    critical_issues: List[ConsistencyIssue] = field(default_factory=list)
    warnings: List[ConsistencyIssue] = field(default_factory=list)
    info: List[ConsistencyIssue] = field(default_factory=list)

    # Statistics
    total_issues: int = 0
    chapters_checked: int = 0
    characters_checked: int = 0
    events_checked: int = 0

    # Metadata
    checked_at: datetime = field(default_factory=datetime.now)
    check_duration_ms: float = 0.0

    def get_all_issues(self) -> List[ConsistencyIssue]:
        """Get all issues sorted by severity"""
        return self.critical_issues + self.warnings + self.info

    def get_issues_by_type(self, issue_type: IssueType) -> List[ConsistencyIssue]:
        """Get issues of a specific type"""
        return [i for i in self.get_all_issues() if i.issue_type == issue_type]

    def get_unresolved_issues(self) -> List[ConsistencyIssue]:
        """Get all unresolved issues"""
        return [i for i in self.get_all_issues() if not i.resolved]


class ConsistencyChecker:
    """
    Main consistency checking engine

    Analyzes project memory to detect contradictions and issues
    """

    def __init__(self, memory_store: MemoryStore, llm_client: Optional[Any] = None):
        """
        Initialize checker with memory store

        Args:
            memory_store: MemoryStore instance for the project
            llm_client: Optional LLM client for semantic checking (Phase 5C)
        """
        self.memory = memory_store
        self.llm_client = llm_client
        self.issue_counter = 0
        self.total_llm_cost = 0.0

    async def run_full_check(
        self,
        author_id: str,
        project_id: str,
        use_llm: bool = False
    ) -> ConsistencyReport:
        """
        Run complete consistency check

        Args:
            author_id: Author ID
            project_id: Project ID
            use_llm: If True and llm_client available, enhance with semantic checking

        Returns:
            ConsistencyReport with all detected issues
        """
        start_time = datetime.now()

        report = ConsistencyReport(
            project_id=project_id,
            author_id=author_id
        )

        # Run all pattern-based checks
        issues: List[ConsistencyIssue] = []

        # Character checks
        issues.extend(self.check_character_attributes())
        issues.extend(self.check_character_presence())

        # Timeline checks
        issues.extend(self.check_timeline_order())
        issues.extend(self.check_timeline_gaps())

        # Plot checks
        issues.extend(self.check_unresolved_plots())
        issues.extend(self.check_abandoned_plots())

        # World building checks
        issues.extend(self.check_world_consistency())

        # LLM Enhancement (Phase 5C) - Semantic analysis
        if use_llm and self.llm_client:
            llm_issues = await self._run_llm_checks()
            issues.extend(llm_issues)

        # Categorize by severity
        for issue in issues:
            if issue.severity == SeverityLevel.CRITICAL:
                report.critical_issues.append(issue)
            elif issue.severity == SeverityLevel.WARNING:
                report.warnings.append(issue)
            else:
                report.info.append(issue)

        # Update statistics
        report.total_issues = len(issues)
        report.characters_checked = len(self.memory.characters)
        report.events_checked = len(self.memory.timeline)

        # Calculate chapters from timeline
        if self.memory.timeline:
            chapters = set(e.chapter for e in self.memory.timeline)
            report.chapters_checked = len(chapters)

        # Duration
        duration = datetime.now() - start_time
        report.check_duration_ms = duration.total_seconds() * 1000

        return report

    # =========================================================================
    # CHARACTER CONSISTENCY CHECKS
    # =========================================================================

    def check_character_attributes(self) -> List[ConsistencyIssue]:
        """
        Check for conflicting character attributes

        Example: Character described as having "blue eyes" in Ch.1
                 but "brown eyes" in Ch.5
        """
        issues = []

        for name, character in self.memory.characters.items():
            # Check if character has conflicting attribute values
            inconsistencies = character.check_consistency()

            for inconsistency in inconsistencies:
                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.CHARACTER_ATTRIBUTE,
                    severity=SeverityLevel.WARNING,
                    title=f"Conflicting attributes for {name}",
                    description=inconsistency,
                    entities_affected=[name],
                    chapters_affected=[
                        character.first_appearance_chapter or 0,
                        character.last_appearance_chapter or 0
                    ],
                    suggestion=f"Review all descriptions of {name} and ensure consistency"
                )
                issues.append(issue)

        return issues

    def check_character_presence(self) -> List[ConsistencyIssue]:
        """
        Check for logical character presence issues

        Example: Character appears after their last appearance
        """
        issues = []

        for name, character in self.memory.characters.items():
            if character.first_appearance_chapter is None:
                continue

            # Check if character appears in events outside their chapter range
            for event in self.memory.timeline:
                if name in event.participants:
                    if event.chapter < character.first_appearance_chapter:
                        issue = ConsistencyIssue(
                            issue_id=self._generate_issue_id(),
                            issue_type=IssueType.CHARACTER_PRESENCE,
                            severity=SeverityLevel.CRITICAL,
                            title=f"{name} appears before introduction",
                            description=(
                                f"{name} participates in an event in Chapter {event.chapter} "
                                f"but is first introduced in Chapter {character.first_appearance_chapter}"
                            ),
                            entities_affected=[name],
                            chapters_affected=[event.chapter, character.first_appearance_chapter],
                            suggestion=f"Update {name}'s first appearance or remove from earlier events"
                        )
                        issues.append(issue)

                    if (character.last_appearance_chapter is not None and
                        event.chapter > character.last_appearance_chapter):
                        issue = ConsistencyIssue(
                            issue_id=self._generate_issue_id(),
                            issue_type=IssueType.CHARACTER_PRESENCE,
                            severity=SeverityLevel.CRITICAL,
                            title=f"{name} appears after last appearance",
                            description=(
                                f"{name} participates in an event in Chapter {event.chapter} "
                                f"but their last appearance was in Chapter {character.last_appearance_chapter}"
                            ),
                            entities_affected=[name],
                            chapters_affected=[character.last_appearance_chapter, event.chapter],
                            suggestion=f"Update {name}'s last appearance or review event timeline"
                        )
                        issues.append(issue)

        return issues

    # =========================================================================
    # TIMELINE CONSISTENCY CHECKS
    # =========================================================================

    def check_timeline_order(self) -> List[ConsistencyIssue]:
        """
        Check for timeline ordering issues

        Example: Event B references event A but occurs before it
        """
        issues = []

        # Check for temporal keywords in event descriptions
        temporal_keywords = {
            'after': ['after', 'following', 'subsequent to'],
            'before': ['before', 'prior to', 'preceding'],
            'during': ['during', 'while', 'as']
        }

        for i, event in enumerate(self.memory.timeline):
            description_lower = event.description.lower()

            # Look for references to other events
            for j, other_event in enumerate(self.memory.timeline):
                if i == j:
                    continue

                # Check if description references the other event
                if any(word in description_lower for word in other_event.description.lower().split()):
                    # Check temporal relationship
                    for relation, keywords in temporal_keywords.items():
                        if any(kw in description_lower for kw in keywords):
                            # Validate ordering
                            if relation == 'after' and event.chapter < other_event.chapter:
                                issue = ConsistencyIssue(
                                    issue_id=self._generate_issue_id(),
                                    issue_type=IssueType.TIMELINE_ORDER,
                                    severity=SeverityLevel.WARNING,
                                    title="Possible timeline contradiction",
                                    description=(
                                        f"Event in Ch.{event.chapter} references happening 'after' "
                                        f"an event in Ch.{other_event.chapter}, but occurs before it"
                                    ),
                                    chapters_affected=[event.chapter, other_event.chapter],
                                    suggestion="Review event ordering or description phrasing"
                                )
                                issues.append(issue)

        return issues

    def check_timeline_gaps(self) -> List[ConsistencyIssue]:
        """
        Check for large gaps in timeline that might indicate missing events
        """
        issues = []

        if len(self.memory.timeline) < 2:
            return issues

        # Check for gaps > 5 chapters with no events
        for i in range(len(self.memory.timeline) - 1):
            current_chapter = self.memory.timeline[i].chapter
            next_chapter = self.memory.timeline[i + 1].chapter
            gap = next_chapter - current_chapter

            if gap > 5:
                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.TIMELINE_GAP,
                    severity=SeverityLevel.INFO,
                    title=f"Large timeline gap detected",
                    description=(
                        f"No significant events recorded between Chapter {current_chapter} "
                        f"and Chapter {next_chapter} ({gap} chapters)"
                    ),
                    chapters_affected=list(range(current_chapter, next_chapter + 1)),
                    suggestion="Consider adding key events or confirm this gap is intentional"
                )
                issues.append(issue)

        return issues

    # =========================================================================
    # PLOT CONSISTENCY CHECKS
    # =========================================================================

    def check_unresolved_plots(self) -> List[ConsistencyIssue]:
        """
        Check for plot threads that are active but haven't been developed
        """
        issues = []

        active_plots = self.memory.list_active_plot_points()

        if not self.memory.timeline:
            return issues

        # Get the latest chapter
        latest_chapter = max(e.chapter for e in self.memory.timeline) if self.memory.timeline else 0

        for plot in active_plots:
            chapters_since_intro = latest_chapter - plot.first_introduced_chapter

            # If plot introduced > 10 chapters ago and has no development
            if chapters_since_intro > 10 and len(plot.development) == 0:
                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.PLOT_UNRESOLVED,
                    severity=SeverityLevel.WARNING,
                    title=f"Stagnant plot thread: {plot.type}",
                    description=(
                        f"Plot '{plot.description}' was introduced in Chapter {plot.first_introduced_chapter} "
                        f"but has no recorded development in {chapters_since_intro} chapters"
                    ),
                    chapters_affected=[plot.first_introduced_chapter, latest_chapter],
                    suggestion="Add development notes or resolve this plot thread"
                )
                issues.append(issue)

        return issues

    def check_abandoned_plots(self) -> List[ConsistencyIssue]:
        """
        Check for plot threads marked as abandoned without resolution
        """
        issues = []

        for plot in self.memory.plot_points.values():
            if plot.status == "abandoned" and plot.resolution_chapter is None:
                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.PLOT_ABANDONED,
                    severity=SeverityLevel.INFO,
                    title=f"Abandoned plot: {plot.type}",
                    description=(
                        f"Plot '{plot.description}' is marked as abandoned but has no resolution chapter. "
                        f"Introduced in Chapter {plot.first_introduced_chapter}"
                    ),
                    chapters_affected=[plot.first_introduced_chapter],
                    suggestion="Consider either resolving or removing this plot thread"
                )
                issues.append(issue)

        return issues

    # =========================================================================
    # WORLD BUILDING CONSISTENCY CHECKS
    # =========================================================================

    def check_world_consistency(self) -> List[ConsistencyIssue]:
        """
        Check for world building contradictions
        """
        issues = []

        # Group world elements by type
        by_type: Dict[str, List[WorldElement]] = {}
        for element in self.memory.world_elements.values():
            if element.type not in by_type:
                by_type[element.type] = []
            by_type[element.type].append(element)

        # Check for conflicting properties within same type
        for element_type, elements in by_type.items():
            for i, elem1 in enumerate(elements):
                for elem2 in elements[i+1:]:
                    # Check for property conflicts
                    common_props = set(elem1.properties.keys()) & set(elem2.properties.keys())
                    for prop in common_props:
                        if elem1.properties[prop] != elem2.properties[prop]:
                            issue = ConsistencyIssue(
                                issue_id=self._generate_issue_id(),
                                issue_type=IssueType.WORLD_CONTRADICTION,
                                severity=SeverityLevel.WARNING,
                                title=f"World building contradiction: {element_type}",
                                description=(
                                    f"Conflicting property '{prop}' for {element_type}: "
                                    f"{elem1.name} has '{elem1.properties[prop]}' but "
                                    f"{elem2.name} has '{elem2.properties[prop]}'"
                                ),
                                entities_affected=[elem1.name, elem2.name],
                                chapters_affected=[
                                    elem1.first_mentioned_chapter,
                                    elem2.first_mentioned_chapter
                                ],
                                conflicting_values={
                                    elem1.name: elem1.properties[prop],
                                    elem2.name: elem2.properties[prop]
                                },
                                suggestion="Review world building notes and ensure consistency"
                            )
                            issues.append(issue)

        return issues

    # =========================================================================
    # LLM-POWERED CHECKS (Phase 5C)
    # =========================================================================

    async def _run_llm_checks(self) -> List[ConsistencyIssue]:
        """Run LLM-powered semantic consistency checks"""
        issues: List[ConsistencyIssue] = []

        # Check character consistency with LLM
        for name, character in self.memory.characters.items():
            llm_issues = await self._check_character_with_llm(name, character)
            issues.extend(llm_issues)

        # Check plot coherence with LLM (if we have plot threads)
        if self.memory.plot_points:
            plot_issues = await self._check_plot_coherence_with_llm()
            issues.extend(plot_issues)

        # Check timeline logic with LLM (if we have events)
        if self.memory.timeline:
            timeline_issues = await self._check_timeline_with_llm()
            issues.extend(timeline_issues)

        return issues

    async def _check_character_with_llm(
        self,
        name: str,
        character: Character
    ) -> List[ConsistencyIssue]:
        """Check character consistency using LLM semantic analysis"""
        if not self.llm_client:
            return []

        try:
            # Format character data
            character_data = llm_prompts.format_character_data_for_checking({
                'name': character.name,
                'role': character.role,
                'description': character.description,
                'traits': character.traits,
                'mentioned_attributes': character.mentioned_attributes,
                'first_appearance_chapter': character.first_appearance_chapter,
                'last_appearance_chapter': character.last_appearance_chapter
            })

            # Call LLM
            prompt = llm_prompts.CHECK_CHARACTER_CONSISTENCY_PROMPT.format(
                character_name=name,
                character_data=character_data
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=llm_prompts.CONSISTENCY_CHECKING_SYSTEM_PROMPT,
                max_tokens=1500,
                temperature=0.3
            )

            # Track cost
            self.total_llm_cost += response.cost_usd

            # Parse response
            result = self._parse_llm_json_response(response.content)
            if not result or not result.get('has_inconsistencies'):
                return []

            # Convert to ConsistencyIssue objects
            issues = []
            for inconsistency in result.get('inconsistencies', []):
                severity_map = {
                    'critical': SeverityLevel.CRITICAL,
                    'moderate': SeverityLevel.WARNING,
                    'minor': SeverityLevel.INFO
                }

                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.CHARACTER_ATTRIBUTE,
                    severity=severity_map.get(inconsistency.get('severity', 'minor'), SeverityLevel.INFO),
                    title=f"LLM: {inconsistency.get('description', '')[:50]}",
                    description=inconsistency.get('description', ''),
                    entities_affected=[name],
                    suggestion=inconsistency.get('suggestion', '')
                )
                issues.append(issue)

            return issues

        except Exception as e:
            logger.error(f"LLM character check failed for {name}: {e}")
            return []

    async def _check_plot_coherence_with_llm(self) -> List[ConsistencyIssue]:
        """Check plot coherence using LLM"""
        if not self.llm_client or not self.memory.plot_points:
            return []

        try:
            # Format plot threads
            plot_threads_data = llm_prompts.format_plot_threads_for_checking([
                {
                    'description': p.description,
                    'type': p.type,
                    'status': p.status,
                    'first_introduced_chapter': p.first_introduced_chapter,
                    'resolution_chapter': p.resolution_chapter,
                    'development': []
                }
                for p in self.memory.plot_points
            ])

            # Format timeline
            timeline_data = llm_prompts.format_timeline_for_checking([
                {
                    'chapter': e.chapter,
                    'description': e.description,
                    'participants': e.participants,
                    'location': e.location,
                    'significance': e.significance
                }
                for e in self.memory.timeline
            ])

            # Call LLM
            prompt = llm_prompts.CHECK_PLOT_COHERENCE_PROMPT.format(
                plot_threads_data=plot_threads_data,
                timeline_data=timeline_data
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=llm_prompts.CONSISTENCY_CHECKING_SYSTEM_PROMPT,
                max_tokens=2000,
                temperature=0.3
            )

            self.total_llm_cost += response.cost_usd

            # Parse and convert to issues
            result = self._parse_llm_json_response(response.content)
            if not result or not result.get('has_issues'):
                return []

            issues = []
            for issue_data in result.get('issues', []):
                issue_type_map = {
                    'plot_hole': IssueType.PLOT_UNRESOLVED,
                    'unresolved': IssueType.PLOT_UNRESOLVED,
                    'abandoned': IssueType.PLOT_ABANDONED
                }

                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=issue_type_map.get(issue_data.get('type', 'unresolved'), IssueType.PLOT_UNRESOLVED),
                    severity=SeverityLevel.WARNING,
                    title=f"LLM: {issue_data.get('description', '')[:50]}",
                    description=issue_data.get('description', ''),
                    suggestion=issue_data.get('suggestion', '')
                )
                issues.append(issue)

            return issues

        except Exception as e:
            logger.error(f"LLM plot check failed: {e}")
            return []

    async def _check_timeline_with_llm(self) -> List[ConsistencyIssue]:
        """Check timeline logic using LLM"""
        if not self.llm_client or not self.memory.timeline:
            return []

        try:
            # Format timeline
            timeline_data = llm_prompts.format_timeline_for_checking([
                {
                    'chapter': e.chapter,
                    'description': e.description,
                    'participants': e.participants,
                    'location': e.location,
                    'significance': e.significance
                }
                for e in self.memory.timeline
            ])

            # Call LLM
            prompt = llm_prompts.CHECK_TIMELINE_LOGIC_PROMPT.format(
                timeline_data=timeline_data
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=llm_prompts.CONSISTENCY_CHECKING_SYSTEM_PROMPT,
                max_tokens=2000,
                temperature=0.3
            )

            self.total_llm_cost += response.cost_usd

            # Parse and convert
            result = self._parse_llm_json_response(response.content)
            if not result or not result.get('has_violations'):
                return []

            issues = []
            for violation in result.get('violations', []):
                issue = ConsistencyIssue(
                    issue_id=self._generate_issue_id(),
                    issue_type=IssueType.TIMELINE_ORDER,
                    severity=SeverityLevel.CRITICAL if violation.get('severity') == 'critical' else SeverityLevel.WARNING,
                    title=f"LLM: {violation.get('description', '')[:50]}",
                    description=violation.get('description', ''),
                    suggestion=violation.get('suggestion', '')
                )
                issues.append(issue)

            return issues

        except Exception as e:
            logger.error(f"LLM timeline check failed: {e}")
            return []

    def _parse_llm_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from LLM"""
        try:
            # Extract JSON from response
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            return None
        except json.JSONDecodeError:
            return None

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _generate_issue_id(self) -> str:
        """Generate unique issue ID"""
        self.issue_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"issue_{timestamp}_{self.issue_counter:04d}"
