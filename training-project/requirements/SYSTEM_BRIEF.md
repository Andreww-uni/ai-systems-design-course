# Learning Knowledge System — Functional Brief

> **Status:** Work in Progress — supplied project definition for instructor review

## How to use this brief

This brief defines the system that every student develops across the course. It is supplied project input, not a requirements-elicitation or architecture-design assignment. The requirements baseline states the binding obligations in testable form. A separately supplied reference architecture will later explain one approved way to realize them.

The [Markdown vault structure contract](VAULT_STRUCTURE.md) states the organization rules for the student-owned canonical vault: folders follow record type, subject and domain grouping uses tags, and meaning-bearing connections use typed relations.

## Purpose and primary user

The learning knowledge system is a workstation-local AI-assisted system that helps a student develop an evidence-based understanding of technical concepts over time. Local means that the student owns the knowledge state and operates the workflow on the student's computer. It does not require a locally hosted foundation model. Its primary user is the student who owns the knowledge state, reviews proposed interpretations, and decides which changes become accepted knowledge.

The system begins with course theory as a shared reproducible source path. A later bounded academic or professional extension does not change the identity of the system.

## Intended outcome

The intended outcome is a knowledge base in which a student can trace a technical concept to its source, understand how it relates to accepted concepts, see which prerequisites are missing, preserve unresolved questions, and obtain answers grounded in retained evidence.

A successful system does more than generate fluent text. It preserves the difference between source evidence, proposed interpretation, accepted knowledge, unresolved questions, and rebuildable representations used for search or visualization.

## Required functional behavior

The complete system is expected to support the following knowledge-development behavior as the course introduces the necessary contracts and components:

- register a source and preserve its provenance;
- identify candidate concepts from that source;
- compare each candidate with concepts already accepted in the knowledge base;
- expose possible duplicates, ambiguity, and contradictions;
- propose typed semantic relations from the supplied course vocabulary;
- identify prerequisite concepts needed to explain a new concept;
- propose adding a missing prerequisite or explicitly deferring it;
- preserve unresolved gaps as questions rather than inventing answers;
- answer learning questions from preserved evidence and expose the supporting sources;
- make accepted relations inspectable through a graph view;
- apply the same controlled workflow to a bounded personal extension.

The course adds these capabilities over time. Naming a concept in the materials does not mean the system already implements it. Laboratory 01 initializes the workspace and system boundary; it does not implement the complete list.

## Knowledge-development scenario

When a source introduces a technical concept, the system first preserves the source identity and provenance. An AI component may then propose a normalized interpretation, relevant existing concepts, typed relations, duplicate candidates, missing prerequisites, and open questions. Deterministic project rules check the available schema and workflow invariants. The student reviews the meaning and either approves or rejects the exact proposal. Only an approved proposal may change canonical knowledge.

The operational loop is therefore:

```text
encounter -> capture -> propose -> validate -> review -> decide -> apply -> verify -> use -> revise
```

This loop separates assistance from authority. Validation can prove that an artifact follows a machine-checkable contract, but it cannot prove that the interpretation is correct, useful, or sufficiently supported.

## State boundaries

The system separates state according to its meaning and recovery method. The following boundaries are requirements, not an implementation architecture.

| State class | Required role | Recovery boundary |
|---|---|---|
| Git-backed project | Course material, requirements, schemas, commands, tests, student implementation, and laboratory evidence | Restored from a controlled Git version or reproduced from project definitions |
| External Markdown vault | Student-owned canonical sources, concepts, questions, and retained audit state | Protected as mutable canonical state; never assumed recoverable from the project repository |
| Derived runtime | Embeddings, vector indexes, compiled graph views, caches, and generated exports | Rebuilt from controlled definitions and canonical vault content |

The external vault remains usable as ordinary Markdown files without Obsidian. Obsidian is a supplied inspection interface, not the owner or canonical format of the knowledge.

## Authority boundaries

The workflow assigns different kinds of authority to different actors. The allocation below applies even when a different model, provider, or agent harness is used.

| Actor or mechanism | May do | Must not do |
|---|---|---|
| AI assistant | Interpret supplied evidence, expose uncertainty, and write candidate proposals | Approve its own proposal or directly mutate accepted canonical knowledge |
| Deterministic project workflow | Validate structures and invariants, bind decisions to exact proposal content, apply approved changes, and report verification results | Decide whether a proposed interpretation is semantically correct |
| Student | Review evidence and meaning, correct a candidate, and explicitly approve or reject it | Treat successful structural validation as proof of semantic quality |
| Course-owned contract | Define shared schemas, relation vocabulary, ownership boundaries, and acceptance conditions | Absorb student-owned knowledge or private vault content into the upstream project |

A human decision applies only to the exact proposal reviewed. If proposal content changes after the decision, the previous approval no longer authorizes application.

Laboratory 01 proposal, decision, and accepted-boundary files are Git-backed project audit artifacts. They are not vault knowledge records. Vault `proposals/`, `decisions/`, and `operations/` records begin when canonical vault knowledge starts to change.

Laboratory 01 enforces the existence, status, completeness, proposal identifier, and proposal digest of the recorded decision. The `recorded_by` value is attribution supplied by the student; it is not authenticated proof of who operated the command. The student must therefore run `decide`. On the normal agent path, evidence shows that the AI proposer edited only the candidate. If no existing agent path can complete the local proposal operation within available access and quota without a new purchase, the instructor may accept the documented manual fallback. The student then authors the same candidate, records the attempted or unavailable path and any available sanitized failure evidence, and makes no AI-authorship claim. This fallback demonstrates artifact control but not live AI/student actor separation. Laboratory 01 does not claim actor-authenticated approval enforcement. That mechanism may be introduced only with a later reviewed agent architecture.

## Shared course path and personal extension

Every student builds the same learning knowledge system from the theory modules of this course. This shared path provides comparable sources, fixtures, and acceptance evidence.

The required personal extension uses a non-sensitive academic or professional area to demonstrate transfer. It remains subject to the same provenance, proposal, validation, human-decision, and verification rules. It must not redefine the project as a different application or require the instructor to judge an entire private domain.

## Laboratory 01 boundary

Laboratory 01 establishes the working contour rather than the full knowledge-processing capability. Its accepted system contribution is limited to:

- a reproducible supported workstation and project environment;
- a correctly owned student fork and working branch;
- the student-owned project and report directories that are intentionally absent upstream;
- an external Markdown vault outside Git;
- registration of the Module 01 theory as the first vault source;
- no structured concept records, graph indexes, or vector indexes;
- one bounded proposal, validation, semantic review, digest-bound decision, and apply cycle used to verify the authority boundary;
- a completed report and evidence set.

The `personal_domain` value used by the Laboratory 01 boundary proposal records only a possible later extension area. It does not select a different system and does not authorize personal-data ingestion.

### Minimum source registration in Laboratory 01

Laboratory 01 uses one minimal source record because the full source, concept, and question schemas are introduced later. The student creates the following ordinary Markdown file inside the external vault:

```text
sources/module-01-ai-engineering-foundations.md
```

The file begins with this YAML front matter. Replace the commit placeholder with the complete 40-character output of `git rev-parse HEAD` from the student's course clone when the source is registered. That hash identifies the theory file in the same Git history the student submits. It is not a check that the clone matches the latest upstream commit.

```yaml
---
record_type: source
source_id: module-01-ai-engineering-foundations
title: "Module 01: AI Engineering Foundations — Theory"
course_path: modules/01_AI_Engineering_Foundations/01_AI_Engineering_Foundations_Theory.md
course_commit: "<40-character Git commit>"
---
```

This record identifies the exact version-controlled theory source without copying the theory into a second editable location. It is a source registration, not a structured concept record. Laboratory 01 creates no files under `concepts/` and builds no graph or vector index.

## Non-goals

The mandatory project excludes several adjacent goals so that its system boundary remains teachable and safe:

- eliciting or formalizing a different set of project requirements;
- asking the student to invent the application architecture;
- modeling a personality or implementing a general personal-information assistant;
- autonomously changing canonical knowledge;
- training a frontier foundation model from scratch;
- providing high-consequence medical, financial, legal, or safety decisions;
- requiring private notes, credentials, real family data, or other sensitive personal data;
- treating a graph visualization, vector index, model output, or agent chat as the canonical knowledge source;
- requiring purchase of a paid model subscription, prepaid API balance, separately billed model use, or commercial cloud infrastructure for the mandatory path. A no-cost account may require provider-side payment-card verification, but card data must remain outside project artifacts and submitted evidence.

## Evidence of success

The complete project is successful only when its claims can be checked from preserved artifacts. Evidence must connect accepted knowledge to sources, AI-generated changes to candidate proposals, human authority to explicit decisions, applied state to the exact approved content, and runtime views to rebuildable canonical inputs.

The detailed obligations and planned verification methods are defined in [REQUIREMENTS_BASELINE.md](REQUIREMENTS_BASELINE.md).
