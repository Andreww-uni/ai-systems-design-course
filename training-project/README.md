# AI Engineering training project

This directory contains the neutral cumulative AI system developed across the eight course
laboratories. It does not depend on the instructor's private repositories or personal data. Every
student works with the same supplied system definition and creates only their own project artefacts.

## Project purpose

The completed system preserves sources and provenance, develops reviewed technical concepts,
identifies missing prerequisites and unresolved questions, exposes typed relations, and answers
questions from retained evidence. AI components may propose interpretations and changes;
deterministic components enforce structural rules; a human retains authority over meaning and every
accepted change.

Canonical knowledge remains in an external Markdown vault owned by the student. Embeddings, indexes,
and graph views are rebuildable derived state rather than canonical records.

## Supplied system contract

The project starts from three supplied documents:

- [`requirements/SYSTEM_BRIEF.md`](requirements/SYSTEM_BRIEF.md) defines the fixed learning knowledge
  system and its boundary;
- [`requirements/REQUIREMENTS_BASELINE.md`](requirements/REQUIREMENTS_BASELINE.md) defines its testable
  obligations and their introduction across the course;
- [`requirements/VAULT_STRUCTURE.md`](requirements/VAULT_STRUCTURE.md) defines the organization and
  authority boundary of the external Markdown vault.

These documents are project inputs. A laboratory may ask the student to interpret or apply them, but
not to replace the supplied system with a different project.

## Directory map

```text
training-project/
  requirements/       supplied system definition and requirements
  platform/           project command-line interface and deterministic workflows
  schemas/            machine-readable record contracts
  fixtures/           supplied deterministic examples and templates
  tests/public/       public acceptance tests for the project contracts
  student/            student-created system artefacts
  reports/            student-created evidence and reports
```

The project README is not a laboratory procedure. Setup, commands, expected results, evidence,
recovery, and submission instructions are defined in the applicable laboratory work:

- [Laboratory 01](../modules/01_AI_Engineering_Foundations/01_AI_Engineering_Foundations_Lab.md)
- [Laboratory 02](../modules/02_Foundation_Models_and_AI_Application_Architecture/02_Foundation_Models_and_AI_Application_Architecture_Lab.md)

Later laboratories extend the same supplied system and document their own operations when those
operations are introduced. Their laboratory files remain the canonical source for those procedures.
