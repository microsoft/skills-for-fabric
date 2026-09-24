# Project Osmos first-run experience

Use this reference when the user explicitly asks what Project Osmos is or invokes it without a concrete task outcome. Never interrupt a concrete task request with onboarding. `SKILL.md` owns normal task setup and runtime.

## Shared contract

- Preserve supplied goals, Lakehouse context, guidance, and draft text.
- Collect only missing setup details.
- Never create, store, or fabricate first-use state.
- If the user already supplied a concrete outcome, continue directly with `SKILL.md`.
- If no outcome was supplied, use the host's choice tool to ask **How would you like to begin?** with:
  1. **Start a task** (`start`)
  2. **Explain Project Osmos to me** (`explain`)
- **Start a task** continues directly to the missing setup fields.
- **Explain Project Osmos to me** uses the content before `## Why do I need to attach a Lakehouse?` in `project-osmos-explainer.md`. Do not include the document title or `Content owner` metadata.
- Use `project-osmos-use-cases.md` only when the user asks for more examples. Return the relevant scenario content without turning it into a walkthrough or another choice menu.

After the user chooses **Start a task**, or after the explanation and any follow-up questions, return to `SKILL.md`. The main skill owns per-run host routing, Lakehouse context selection, authentication, and task setup.
