---
name: openai-plan-reviewer
description: Consults the local OpenAI-compatible API proxy on port 10531 to review, evaluate, and refine implementation plans (implementation_plan.md) before execution. Use when creating or updating technical plans.
argument-hint: "[path/to/plan.md]"
---

# OpenAI Local Plan Reviewer Skill

This skill allows the agent to send implementation plans to the locally running OpenAI proxy (`http://127.0.0.1:10531/v1`) to obtain automated architectural reviews, risk assessments, and step refinements.

## When to Use This Skill
- Whenever a new `implementation_plan.md` or technical proposal is drafted or updated.
- Before executing complex, multi-step refactorings or infrastructure changes.
- When you want an automated second opinion from your local ChatGPT session without hitting public cloud endpoints.

## Execution Workflow

1. **Verify Local Proxy Availability**:
   Run the helper script against your target plan file:
   ```bash
   python .agents/skills/openai-plan-reviewer/scripts/consult_plan_api.py --plan implementation_plan.md
   ```

2. **Handle Script Responses**:
   - **If the proxy is online**: The script will execute a multi-turn review loop and print structured feedback (strengths, edge-case risks, and suggested refinements).
   - **If the proxy is offline**: The script gracefully outputs a diagnostic notice:
     `[Notice] Local OpenAI proxy at port 10531 is offline`.
     *Action*: Proceed with your existing plan without failing or stopping execution. You can optionally remind the user to start `npx openai-oauth@latest` if they desire local AI reviews.

3. **Incorporate Feedback**:
   - If feedback was received from the local proxy, review the recommendations and update `implementation_plan.md` accordingly before requesting user confirmation.
