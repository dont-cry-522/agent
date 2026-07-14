---
name: rag-design
description: Use ONLY when adding new features to the yuque-agent RAG project. Enforces design-first methodology — explain why before coding, test with real queries, document before/after differences.
---

# RAG Design Thinking

When adding any new feature to this project, follow this methodology:

## Before writing code

1. **Explain the design** — why is this module/feature being implemented this way?
2. **Identify the responsibilities** — what does this module own, and what does it NOT own?
3. **Clarify boundaries** — what should NOT be put in this module, and why?

Reference these existing design patterns from the project:

| Decision | Principle |
|----------|-----------|
| Retriever is independent | Single responsibility; swap vector DB without touching other code |
| PromptBuilder is separate | Templates iterate fastest; decouple from business logic |
| LLM doesn't query FAISS | Avoid coupling HTTP client with vector search |
| Context doesn't participate in Embedding | Prevent structural information from polluting semantic signals |
| Context is used in PromptBuilder | Context helps LLM understand results, not find them |
| RAG enhances Prompt, not LLM | Model weights never change; it's Prompt Augmentation |

## After writing code

1. **Run test queries** — pick 2-3 real questions from the knowledge base
2. **Compare before/after** — show the output difference concretely
3. **Verify the pipeline** — ensure all downstream modules still work

## After verifying

1. **Record findings** — append to `DESIGN.md` with concrete examples
2. **Document the "why"** — include both the design rationale and actual query results
3. **Note any trade-offs** — what was gained, what was sacrificed

## Keep documentation current (MANDATORY)

After EVERY feature implementation, update ALL of these files without being asked:

| File | What to update |
|------|---------------|
| `DESIGN.md` | Add new design Q&A + before/after comparison + update roadmap status |
| `GUIDE.md` | Update usage commands, tech stack, architecture, or setup steps if changed |
| `SESSION.md` | Update completed phases table, current status, next task |

Never skip this step. The user should never have to ask "did you update the docs?"

## Design questions to always answer

For every new module or feature:

- Why is this module independent?
- What happens if this module is combined with another? What breaks?
- Why does X NOT participate in Y?
- Does this enhance the Prompt or the Model? How?
- How would you test this module in isolation?
- What is the migration path if this module needs to be replaced?

## Anti-patterns to avoid

- Mixing HTTP logic into non-LLM modules
- Putting search/retrieval logic into the LLM module
- Hard-coding prompt templates in business logic
- Embedding structural metadata (headings, paths) into semantic vectors
- Skipping test queries before claiming improvement
