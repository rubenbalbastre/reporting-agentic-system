from agents import function_tool


@function_tool
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on task progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the workflow for quality decision-making.

    When to use:
    - After receiving results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing gaps: What specific information am I still missing?
    - Before concluding: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"
