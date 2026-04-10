# Stagehand Execution Summary

## YOUR GOAL
Summarize the conversation history of the current thread into a valid JSON matching the `PlanSummary` schema. This summary will be presented to the admin for final approval before execution.

## DIRECTIVES
1. **Analyze Decisions**: Identify finalized roles, channels, and permissions.
2. **Justification**: Why are these changes happening?
3. **Consensus**: What was the final agreed-upon decision?
4. **Actions**: A high-level list of technical changes (e.g., "Set #general to private").
5. **PROHIBITED**: 
   - DO NOT include raw JSON from the previous planning phase.
   - DO NOT mention technical IDs.

## OUTPUT FORMAT
Return a valid JSON object matching the `PlanSummary` schema.
