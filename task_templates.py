"""
Archetype-appropriate starter tasks per bucket.

Each entry maps a bucket ID to a list of (project_name_keyword, tasks) tuples.
When we can't match a project name to a keyword, we fall back to `_default`.
"""

# Bucket-level default tasks used when a project name doesn't match any keyword.
BUCKET_DEFAULT_TASKS: dict[str, list[str]] = {
    "BUILD": [
        "Define requirements and scope",
        "Create initial design or prototype",
        "Set up tracking and milestones",
    ],
    "FIX": [
        "Identify root cause",
        "Implement fix",
        "Verify resolution and document",
    ],
    "IMPROVE": [
        "Measure current baseline",
        "Identify top improvement lever",
        "Implement and validate improvement",
    ],
    "OPERATE": [
        "Review status and priorities",
        "Execute recurring checklist",
        "Log outcome and next action",
    ],
    "THINK": [
        "Gather relevant inputs",
        "Synthesise key insights",
        "Draft decision or recommendation",
    ],
    "PERSONAL": [
        "Define success criteria",
        "Schedule first session",
        "Track progress weekly",
    ],
}

# Archetype-tuned overrides keyed by (element, bucket_id).
# Only needs to cover cases where the defaults would feel off.
ARCHETYPE_BUCKET_TASKS: dict[tuple[str, str], list[str]] = {
    # Metal / Strategic Commander
    ("Metal", "BUILD"): [
        "Define sprint goals and OKRs",
        "Identify critical path items",
        "Assign owners and deadlines",
    ],
    ("Metal", "THINK"): [
        "Review competitive landscape",
        "Synthesise intel into decision brief",
        "Schedule architectural review",
    ],
    ("Metal", "OPERATE"): [
        "Run weekly ops review",
        "Send stakeholder status update",
        "Clear inbox and action items",
    ],
    # Wood / Visionary Builder
    ("Wood", "BUILD"): [
        "Draft concept brief",
        "Prototype key interaction",
        "Share with early adopters for feedback",
    ],
    ("Wood", "THINK"): [
        "Write vision document",
        "Map emerging market opportunities",
        "Schedule blue-sky brainstorm",
    ],
    # Water / Adaptive Navigator
    ("Water", "THINK"): [
        "Analyse relevant data patterns",
        "Map risk scenarios",
        "Draft adaptive response plan",
    ],
    ("Water", "OPERATE"): [
        "Check monitoring dashboards",
        "Triage support queue",
        "Update runbooks with lessons learned",
    ],
    # Fire / Energetic Catalyst
    ("Fire", "BUILD"): [
        "Rapid prototype first iteration",
        "Run energy check-in with team",
        "Launch and collect fast feedback",
    ],
    ("Fire", "OPERATE"): [
        "Run daily standup",
        "Celebrate recent win",
        "Remove one blocker for the team",
    ],
    # Earth / Steady Architect
    ("Earth", "BUILD"): [
        "Document requirements thoroughly",
        "Validate architectural foundation",
        "Define acceptance criteria",
    ],
    ("Earth", "OPERATE"): [
        "Review SLA metrics",
        "Update runbook for this week",
        "Confirm on-call schedule",
    ],
}


def default_tasks_for(element: str, bucket_id: str) -> list[str]:
    """Return starter tasks for the given element + bucket combination."""
    key = (element, bucket_id)
    return ARCHETYPE_BUCKET_TASKS.get(key, BUCKET_DEFAULT_TASKS.get(bucket_id, [
        "Define goal and success criteria",
        "Take first concrete action",
        "Review and iterate",
    ]))
