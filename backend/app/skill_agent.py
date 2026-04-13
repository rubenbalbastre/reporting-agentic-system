from agents import Agent


def build_skill_agent() -> Agent:
    instructions = (
        "You create reusable skills from user teaching requests. "
        "Return ONLY valid JSON with keys: skill_name, description, skill_markdown. "
        "Constraints: "
        "1) skill_name must be short, lowercase, hyphenated. "
        "2) description must be one sentence for search preview. "
        "3) skill_markdown must be a full SKILL.md document and must start with YAML frontmatter containing name and description. "
        "4) Keep instructions practical and concise. "
        "5) Do not wrap JSON in markdown code fences."
    )

    return Agent(
        name="skill_agent",
        instructions=instructions,
        model="gpt-5.4-nano",
    )
