# ALKEM — Design & Learning Notes

This document captures technical, architectural, product, and business lessons that emerge while building ALKEM.

It is not a specification and it is not a chronological project log.

Its purpose is to turn concrete engineering decisions into reusable knowledge:

- technical interview preparation;
- architecture and design review;
- deeper study of weak areas;
- product reasoning;
- portfolio storytelling.

The guiding idea is simple:

> Learn concepts through real decisions rather than memorizing definitions in isolation.

---

# 1. Capability-specific protocols vs. a fat provider abstraction

## The problem observed in ALKEM

The original provider gateway exposed a single abstraction:

```python
AIProviderPort
```

A provider implementing this contract was expected to support chat completion, streaming, embeddings, and cost estimation.

This initially looked convenient because every AI provider could be represented through one interface. The problem became visible with Anthropic: its adapter did not support embeddings, but the common interface required an `embed()` method anyway. The implementation therefore exposed the method only to raise `NotImplementedError`.

This is a design smell. The adapter technically satisfied the shape of the interface, but it could not satisfy its semantic promise.

The contract was saying:

> “Anything implementing AIProviderPort can perform embeddings.”

The actual system was saying:

> “Some implementations can, some cannot; call the method and find out at runtime.”

The abstraction was therefore hiding an important difference rather than modelling it.

---

## Decision

Replace the monolithic provider port with capability-specific protocols:

```python
ChatProvider
EmbeddingProvider
CostEstimator
```

A concrete adapter implements only the capabilities that it actually supports.

```text
OpenAIAdapter
 ├── ChatProvider
 ├── EmbeddingProvider
 └── CostEstimator

AnthropicAdapter
 ├── ChatProvider
 └── CostEstimator

OllamaAdapter
 ├── ChatProvider
 ├── EmbeddingProvider
 └── CostEstimator
```

No fake capability is required.

---

# 2. Related design principles

## Interface Segregation Principle — ISP

This is the SOLID principle most directly related to the change.

> Clients and implementations should not be forced to depend on operations they do not need or cannot support.

The original `AIProviderPort` bundled several capabilities into one contract. Separating them allows each implementation to depend only on the relevant abstraction.

This does not mean that every method should become its own interface. Over-segregation creates another kind of complexity. Prematurely creating `CanComplete`, `CanStream`, `CanEstimateInputCost`, `CanEstimateOutputCost`, `CanEmbedSingleInput`, and `CanEmbedMultipleInputs` would make the model harder to understand without solving a real problem.

The design goal is not “make interfaces as small as possible”; it is “make interfaces as cohesive as necessary.” For now, `complete()` and `stream()` remain together under `ChatProvider` because they represent closely related ways of consuming the same capability.

## Liskov Substitution Principle — LSP

A subtype or implementation should be usable wherever its abstraction is expected without surprising the caller.

The previous design weakened this principle. A caller receiving an `AIProviderPort` could reasonably assume that `provider.embed(...)` was valid. With `AnthropicAdapter`, that assumption produced a runtime `NotImplementedError`.

The new design makes the substitution contract more truthful: if an object is treated as an `EmbeddingProvider`, embeddings should actually work.

## Dependency Inversion Principle — DIP

Higher-level ALKEM code should depend on abstractions rather than concrete vendors. The application should work with concepts such as `ChatProvider` and `EmbeddingProvider`, rather than `OpenAIAdapter`, `AnthropicAdapter`, or `OllamaAdapter`.

Provider-specific details remain at the system boundary. This allows the core to depend on capabilities instead of vendor implementations.

## Composition over inheritance

The new model represents a provider as a composition of capabilities. A provider does not need to inherit from a large base class containing every possible AI feature. Instead, an implementation can satisfy several independent contracts.

This keeps behavior modular and avoids large inheritance hierarchies.

## Connection with Protocol-Oriented Programming

This approach is conceptually close to Protocol-Oriented Programming as commonly used in Swift. Instead of asking what large class hierarchy an object belongs to, the system asks what capabilities the type provides.

A type can satisfy several protocols without inheriting implementation or identity from a common fat superclass. Python's structural `Protocol` mechanism provides a similar design tool.

---

# 3. Is this a design pattern?

Not in the traditional Gang of Four sense. There is no specific GoF pattern called “split the AI provider into capability protocols.”

It is better described as the application of:

- Interface Segregation;
- structural typing;
- capability-based design;
- composition;
- dependency inversion.

This distinction matters. Good architecture is not primarily about identifying which named pattern can be inserted into a system. Patterns are tools; the real goal is to model the problem accurately.

---

# 4. A useful design rule: interfaces should tell the truth

An interface is a promise. If an interface exposes `embed(...)`, callers should not need vendor knowledge to determine whether calling it is safe.

An abstraction that requires runtime knowledge of its concrete implementation is leaking information.

This gives ALKEM a useful informal principle:

> Interfaces should tell the truth about the capabilities they represent.

This principle can be applied well beyond AI providers.

---

# 5. Why no backwards compatibility layer?

Codex initially proposed preserving `AIProviderPort` as a deprecated compatibility alias during the transition. We deliberately rejected that proposal.

## Reason

ALKEM currently has no external consumers depending on this public API. Maintaining compatibility would therefore solve a problem that does not exist yet.

It would introduce:

- another name to understand;
- migration documentation;
- deprecated API surface;
- additional tests;
- future cleanup work.

The cheaper moment to make a breaking architectural correction is before users depend on the API.

## General lesson

Backward compatibility has value when someone is relying on the existing contract. Without consumers, compatibility can become accidental complexity.

Do not pay migration costs before there is something to migrate.

---

# 6. Scope reduction as architecture

Several proposals were deliberately postponed:

- Model Registry;
- automatic provider routing;
- retry/fallback orchestration;
- complex streaming event hierarchies;
- dynamic pricing infrastructure;
- RAG inside the Provider Gateway;
- memory inside the Provider Gateway;
- tools/agents inside the Provider Gateway;
- compatibility abstractions for unused APIs.

These are not missing features by accident. They are explicit design decisions.

The Provider Gateway currently has one responsibility:

> Translate provider-independent AI capability contracts into provider-specific communication and normalize the results back into provider-independent concepts.

Everything else needs evidence before entering that boundary.

---

# 7. Product lesson: precision before surface area

ALKEM is currently being developed as a portfolio and learning project. Its value is therefore not proportional to its line count.

A smaller system with clear boundaries, coherent abstractions, meaningful tests, documented trade-offs, and real use cases is more valuable than a large system containing infrastructure copied from enterprise architectures without demonstrated need.

A portfolio project should maximize:

```text
signal / complexity
```

not:

```text
features / repository
```

The question behind each new abstraction should be: “What concrete problem does this solve in ALKEM today?” If the answer is hypothetical, implementation can usually wait.

---

# 8. Business/product lesson: opportunity cost is part of architecture

Every feature has more than an implementation cost. It also consumes attention, learning time, debugging time, test surface, documentation effort, cognitive load, and portfolio explanation time.

Building infrastructure that is not necessary can delay the functionality that actually demonstrates product value. Architecture therefore has an opportunity-cost dimension.

For ALKEM, implementing an elaborate routing system before having a useful code workflow would be technically interesting but strategically weak. The product goal should drive architectural sequencing.

---

# 9. Side Chat vs. Ephemeral Branch

An important distinction emerged between a product concept and an architecture concept.

## Product concept: Side Chat

A user can temporarily ask a secondary question without disrupting the main conversation.

```text
Main:
A → B → C ─────────────→ D
          │
          └── Side Chat
                 Q → A
```

The user returns to the primary conversation after resolving the secondary question.

## Architecture concept: Ephemeral Branch

The system represents that interaction as a branch from a particular point in a conversation. The branch inherits relevant parent context, owns its own messages, does not automatically contaminate the parent, can be discarded, and may later support explicit promotion of information back into the parent.

This leads to an important architectural insight:

> Conversation history is not the same thing as model context.

The system may persist many events while sending only selected information to a model.

---

# 10. Human + AI development workflow

ALKEM is also an experiment in AI-assisted software engineering. The intended division of responsibilities is approximately:

```text
Human + architectural discussion
        ↓
bounded engineering decision
        ↓
small implementation task
        ↓
Codex
        ↓
diff + tests
        ↓
human review
        ↓
architecture review
        ↓
next task
```

The purpose is not to maximize generated code. It is to maximize useful iteration while maintaining human understanding of the system.

---

# 11. Why small Codex tasks?

Large prompts such as “Implement ALKEM” would give the coding agent too much freedom to make architectural decisions implicitly.

Instead, tasks are deliberately narrow:

```text
1. Split provider capabilities.
2. Introduce embedding request/result contracts.
3. Normalize streaming.
4. Improve HTTP lifecycle and error boundaries.
5. Correct cost estimation.
```

This keeps diffs reviewable, regressions easier to isolate, decisions explicit, commits useful, generated code understandable, and learning continuous.

---

# 12. Tests as part of the agent contract

A Codex task is not considered complete merely because code was generated.

```text
edit
 ↓
run tests
 ↓
failure
 ↓
inspect
 ↓
fix
 ↓
run tests
 ↓
green
```

The first capability refactor ended with `5 passed`. This establishes the baseline expectation that the coding agent must be capable of validating its own changes.

Human review remains necessary, but the human should not become the agent's manual test runner.

---

# 13. How to defend the capability decision in an interview

> The original provider abstraction bundled unrelated capabilities. That forced adapters to expose operations they did not actually support; Anthropic embeddings were the concrete example, where the interface required a method that only raised `NotImplementedError`.
>
> I split the abstraction into capability-specific protocols such as `ChatProvider`, `EmbeddingProvider`, and `CostEstimator`. That made the contracts truthful and improved interface segregation and substitutability without introducing a large hierarchy.
>
> I deliberately avoided splitting every operation into its own interface because that would have created unnecessary fragmentation. The goal was cohesive capability boundaries, not maximum interface count.

A stronger follow-up if asked about trade-offs:

> The trade-off is that consumers that need several capabilities now depend on more than one protocol. I consider that preferable because the dependency is explicit and reflects the actual requirements of the use case.

---

# 14. Questions worth studying further

## Python structural typing

- How does `typing.Protocol` work?
- How does structural typing differ from nominal interfaces?
- What does `@runtime_checkable` actually guarantee?
- When should runtime protocol checks be avoided?

## SOLID

- Interface Segregation Principle.
- Liskov Substitution Principle.
- Dependency Inversion Principle.
- How SOLID can be over-applied.

## Architecture

- Ports & Adapters / Hexagonal Architecture.
- Capability-based API design.
- Composition vs inheritance.
- Domain boundaries.
- Semantic vs syntactic interface compliance.

## Product engineering

- Scope management.
- Opportunity cost.
- MVP vs platform architecture.
- Portfolio signal.
- When to generalize an abstraction.

---

# 15. Template for future learning entries

Each important ALKEM decision can be documented using this structure.

## Concept

What technical/product concept emerged?

## Problem observed in ALKEM

What concrete behavior or limitation exposed the issue?

## Decision

What was changed or intentionally left unchanged?

## Related principles

Which architecture, design, product, or business principles relate to the decision?

## Alternatives considered

What else could have been done?

## Trade-offs

What did the chosen approach improve, and what did it cost?

## Interview explanation

How could the decision be explained clearly in two or three minutes?

## Further study

Which underlying topics deserve deeper review?
