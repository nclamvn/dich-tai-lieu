"""
LLM Prompt Templates for Memory Extraction and Consistency Checking (Phase 5C)

Carefully crafted prompts for optimal extraction and checking results.
"""

# ==============================================================================
# MEMORY EXTRACTION PROMPTS
# ==============================================================================

EXTRACT_CHARACTERS_PROMPT = """You are analyzing a chapter from a novel to extract character information.

Read the following chapter carefully and extract all characters mentioned:

<chapter>
{chapter_content}
</chapter>

For each character, identify:
1. Name (full name and any nicknames/aliases)
2. Role (protagonist, antagonist, supporting, minor)
3. Physical description (if mentioned)
4. Personality traits (if shown)
5. Relationships with other characters
6. Character arc/development in this chapter

Return your analysis as a JSON array of character objects:

```json
[
  {{
    "name": "Character's full name",
    "aliases": ["Nickname1", "Nickname2"],
    "role": "protagonist|antagonist|supporting|minor",
    "physical_attributes": {{
      "age": "description if mentioned",
      "height": "description if mentioned",
      "eye_color": "color if mentioned",
      "hair_color": "color if mentioned",
      "other": "any other physical details"
    }},
    "traits": ["trait1", "trait2", "trait3"],
    "relationships": {{
      "Character Name": "relationship description"
    }},
    "arc_in_chapter": "brief description of character development in this chapter"
  }}
]
```

Only include characters who actually appear or are meaningfully discussed in this chapter.
Be precise and extract only information explicitly stated or clearly implied."""

EXTRACT_EVENTS_PROMPT = """You are analyzing a chapter from a novel to extract significant events.

Read the following chapter carefully:

<chapter>
{chapter_content}
</chapter>

Chapter number: {chapter_number}

Identify all significant events in this chapter. An event should be:
- A key action or occurrence that moves the plot forward
- A revelation or discovery
- A significant interaction between characters
- A decision or turning point

For each event, provide:
1. Brief description (1-2 sentences)
2. Characters involved
3. Location (if mentioned)
4. Significance to the plot
5. Consequences or implications

Return your analysis as a JSON array:

```json
[
  {{
    "description": "Brief description of what happened",
    "participants": ["Character1", "Character2"],
    "location": "Location name if mentioned",
    "significance": "Why this event matters to the plot",
    "consequences": ["Impact1", "Impact2"]
  }}
]
```

Focus on events that matter to the story. Skip mundane details unless they're plot-relevant."""

EXTRACT_PLOT_THREADS_PROMPT = """You are analyzing a chapter from a novel to identify plot threads.

Read the following chapter:

<chapter>
{chapter_content}
</chapter>

Chapter number: {chapter_number}

Identify any plot threads (storylines, conflicts, mysteries, goals) that are:
1. Introduced in this chapter (new plot threads)
2. Developed in this chapter (existing threads that progress)
3. Resolved in this chapter (threads that conclude)

For each plot thread, provide:
1. Type (main_plot, subplot, mystery, conflict, goal, romance, etc.)
2. Description
3. Status (introduced, developing, resolved)
4. Characters involved
5. Development notes (what changed in this chapter)

Return as JSON array:

```json
[
  {{
    "type": "mystery|conflict|romance|goal|subplot|main_plot",
    "description": "Brief description of this plot thread",
    "status": "introduced|developing|resolved",
    "characters_involved": ["Character1", "Character2"],
    "development": "What happened with this thread in this chapter",
    "hints_or_clues": ["Any foreshadowing or clues about where this is going"]
  }}
]
```

Be thoughtful about what constitutes a distinct plot thread."""

EXTRACT_WORLD_ELEMENTS_PROMPT = """You are analyzing a chapter from a novel to extract world-building elements.

Read the following chapter:

<chapter>
{chapter_content}
</chapter>

Identify world-building elements such as:
1. Locations (cities, buildings, rooms, landmarks)
2. Rules (laws, social norms, physics, magic systems)
3. Lore (history, legends, cultural practices)
4. Organizations (governments, companies, groups)
5. Technology or magical items

For each element, provide:
1. Type (location, rule, lore, organization, item)
2. Name
3. Description
4. Properties or characteristics
5. Significance to the story

Return as JSON array:

```json
[
  {{
    "type": "location|rule|lore|organization|item",
    "name": "Name of the element",
    "description": "Detailed description",
    "properties": {{
      "key1": "value1",
      "key2": "value2"
    }},
    "significance": "Why this matters to the story"
  }}
]
```

Only include elements that are explicitly described or established."""

# ==============================================================================
# CONSISTENCY CHECKING PROMPTS
# ==============================================================================

CHECK_CHARACTER_CONSISTENCY_PROMPT = """You are checking a character's consistency across a story.

Character: {character_name}

Here is all the information we have about this character from different chapters:

<character_data>
{character_data}
</character_data>

Analyze this data for any contradictions or inconsistencies in:
1. Physical attributes (age, appearance, etc.)
2. Personality traits or behavior patterns
3. Backstory or history
4. Relationships with other characters
5. Capabilities or limitations

Return your analysis as JSON:

```json
{{
  "has_inconsistencies": true/false,
  "inconsistencies": [
    {{
      "category": "physical|personality|backstory|relationship|capability",
      "description": "Detailed description of the inconsistency",
      "conflicting_info": {{
        "source1": "First version of information",
        "source2": "Conflicting version"
      }},
      "severity": "critical|moderate|minor",
      "suggestion": "How to resolve this inconsistency"
    }}
  ],
  "overall_assessment": "Brief summary of character consistency"
}}
```

Be thorough but fair - only flag genuine contradictions, not natural character development."""

CHECK_PLOT_COHERENCE_PROMPT = """You are checking the coherence of plot threads in a story.

Here are the plot threads we're tracking:

<plot_threads>
{plot_threads_data}
</plot_threads>

Here is the timeline of events:

<timeline>
{timeline_data}
</timeline>

Analyze for:
1. Plot holes (events that don't make sense given earlier events)
2. Unresolved threads (introduced but never addressed)
3. Contradictions in causality (effects before causes)
4. Pacing issues (threads that stagnate too long)
5. Abandoned threads (started but dropped without resolution)

Return as JSON:

```json
{{
  "has_issues": true/false,
  "issues": [
    {{
      "type": "plot_hole|unresolved|contradiction|pacing|abandoned",
      "description": "Detailed description of the issue",
      "affected_threads": ["Thread1", "Thread2"],
      "severity": "critical|moderate|minor",
      "suggestion": "How to address this issue"
    }}
  ],
  "overall_coherence_score": 0-10,
  "summary": "Brief assessment of plot coherence"
}}
```

Consider the story's genre and style when assessing."""

CHECK_TIMELINE_LOGIC_PROMPT = """You are checking the logical consistency of story events.

Here is the timeline of events:

<timeline>
{timeline_data}
</timeline>

Analyze for:
1. Temporal impossibilities (character in two places at once)
2. Causality violations (effects before causes)
3. Timeline gaps that need explanation
4. Unrealistic time compression or expansion
5. Character presence violations (appearing when they shouldn't be able to)

Return as JSON:

```json
{{
  "has_violations": true/false,
  "violations": [
    {{
      "type": "temporal|causality|gap|pacing|presence",
      "description": "Detailed description of the problem",
      "affected_events": ["Event1", "Event2"],
      "severity": "critical|moderate|minor",
      "suggestion": "How to fix this"
    }}
  ],
  "timeline_quality_score": 0-10,
  "summary": "Overall timeline assessment"
}}
```

Account for the genre (fantasy may have time travel, etc.)."""

# ==============================================================================
# SYSTEM PROMPTS
# ==============================================================================

MEMORY_EXTRACTION_SYSTEM_PROMPT = """You are an expert literary analyst specialized in extracting structured information from narrative text.

Your task is to analyze story chapters and extract:
- Characters and their attributes
- Significant events and their consequences
- Plot threads and their development
- World-building elements

Be precise and factual. Only extract information that is explicitly stated or clearly implied in the text.
Do not make assumptions or add information not present in the source material.

Always return valid JSON that matches the requested schema exactly."""

CONSISTENCY_CHECKING_SYSTEM_PROMPT = """You are an expert story editor specialized in identifying continuity errors and plot holes.

Your task is to analyze story data and identify:
- Character inconsistencies
- Plot contradictions
- Timeline violations
- Logical impossibilities

Be thorough but fair:
- Flag genuine errors, not natural character development
- Consider the genre and style of the story
- Distinguish between critical errors and minor issues
- Provide constructive suggestions for fixes

Always return valid JSON that matches the requested schema exactly."""

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_character_data_for_checking(character_dict: dict) -> str:
    """Format character data for consistency checking prompt"""
    lines = []

    lines.append(f"Name: {character_dict.get('name', 'Unknown')}")
    lines.append(f"Role: {character_dict.get('role', 'Unknown')}")

    if character_dict.get('aliases'):
        lines.append(f"Aliases: {', '.join(character_dict['aliases'])}")

    if character_dict.get('description'):
        lines.append(f"Description: {character_dict['description']}")

    if character_dict.get('traits'):
        lines.append(f"Traits: {', '.join(character_dict['traits'])}")

    if character_dict.get('mentioned_attributes'):
        lines.append("\nRecorded Attributes:")
        for attr, values in character_dict['mentioned_attributes'].items():
            lines.append(f"  {attr}: {', '.join(values)}")

    if character_dict.get('first_appearance_chapter'):
        lines.append(f"\nFirst Appearance: Chapter {character_dict['first_appearance_chapter']}")

    if character_dict.get('last_appearance_chapter'):
        lines.append(f"Last Appearance: Chapter {character_dict['last_appearance_chapter']}")

    return "\n".join(lines)


def format_plot_threads_for_checking(plot_threads: list) -> str:
    """Format plot threads for coherence checking"""
    lines = []

    for i, thread in enumerate(plot_threads, 1):
        lines.append(f"\n=== Thread {i}: {thread.get('description', 'Unknown')} ===")
        lines.append(f"Type: {thread.get('type', 'Unknown')}")
        lines.append(f"Status: {thread.get('status', 'Unknown')}")
        lines.append(f"Introduced: Chapter {thread.get('first_introduced_chapter', '?')}")

        if thread.get('resolution_chapter'):
            lines.append(f"Resolved: Chapter {thread['resolution_chapter']}")

        if thread.get('development'):
            lines.append("Development:")
            for dev in thread['development']:
                lines.append(f"  - Chapter {dev.get('chapter', '?')}: {dev.get('note', '')}")

    return "\n".join(lines)


def format_timeline_for_checking(events: list) -> str:
    """Format timeline events for logic checking"""
    lines = []

    for event in sorted(events, key=lambda e: e.get('chapter', 0)):
        lines.append(f"\n--- Chapter {event.get('chapter', '?')} ---")
        lines.append(f"Event: {event.get('description', 'Unknown')}")

        if event.get('participants'):
            lines.append(f"Participants: {', '.join(event['participants'])}")

        if event.get('location'):
            lines.append(f"Location: {event['location']}")

        if event.get('significance'):
            lines.append(f"Significance: {event['significance']}")

    return "\n".join(lines)
