# Learning Knowledge System — Requirements Baseline

> **Status:** Work in Progress — supplied requirements for instructor review
>
> **Decision owner:** Course instructor
>
> **Scope:** What the learning knowledge system must do. This is not a laboratory schedule.

## Purpose and interpretation

This baseline states what the learning knowledge system must do and how each obligation can be verified. It does not prescribe the internal architecture. It does not say in which laboratory a capability first appears. Students receive these requirements as project input; they are not asked to elicit, replace, or formalize them.

`MUST` identifies a mandatory obligation. Each requirement has a stable identifier and a planned verification method.

Laboratory 01 does not build the whole system. Its own acceptance section lists only what that laboratory must show. Naming a concept in the course materials does not mean the system already has to implement it.

The Module 01 source registration is a controlled initialization operation, not a governed semantic change. Laboratory 01 proposal, decision, and accepted-boundary files are Git-backed project audit artifacts. They are not vault knowledge records. Vault `proposals/`, `decisions/`, and `operations/` records appear when canonical vault knowledge starts to change.

## System scope

The following requirements fix the project identity, its user, and the boundary between supplied project decisions and student work.

| ID | Requirement | Planned verification |
|---|---|---|
| SYS-001 | The course project MUST remain a workstation-local AI-assisted learning knowledge system for technical concepts. Local refers to student-owned state on the student's computer, not to a requirement that inference use a local model. | Inspect the supplied project identity and the accepted system-boundary artifact. |
| SYS-002 | The primary user MUST be the student who owns the knowledge state. | Inspect the supplied project identity and the ownership boundary. |
| SYS-003 | Final semantic decision authority MUST remain with the student who owns the knowledge state. | Inspect workflow roles and the recorded student decision. |
| SYS-004 | A personal academic or professional area MUST remain a bounded extension of the fixed system rather than redefine its identity. | Compare the accepted boundary and later personal-extension artifact with `SYS-001`. |
| SYS-005 | The course distribution MUST supply the project requirements before any laboratory depends on them. | Confirm that this baseline is present in the published training project and referenced by the dependent laboratory. |
| SYS-006 | The course distribution MUST supply a reviewed reference architecture before a laboratory requires implementation against that architecture. | Confirm that the referenced architecture is present and instructor-approved before the dependent laboratory is released. |
| SYS-007 | A laboratory MUST NOT assign elicitation or replacement of this supplied requirements baseline as student work. | Inspect every released laboratory goal, step, and submission item for a conflicting requirements task. |
| SYS-008 | Laboratory 01 MUST NOT assign application-architecture design as student work. | Inspect the Laboratory 01 goal, steps, accepted boundary schema, and submission manifest. |
| SYS-009 | The mandatory project MUST NOT train a foundation model from scratch. | Inspect mandatory dependencies, commands, laboratory goals, and submission artifacts for model-weight training or a training pipeline. |
| SYS-010 | The mandatory project MUST NOT accept a medical, financial, legal, or safety-critical decision as its intended outcome. | Reject any mandatory fixture, accepted boundary, or personal-extension definition whose intended outcome makes one of these decisions. |

## Functional requirements

These requirements define the observable knowledge-development capabilities of the system.

| ID | Requirement | Planned verification |
|---|---|---|
| FUN-001 | The system MUST register each accepted source used to develop knowledge. | Create the Module 01 source record and inspect it at the path defined in the functional brief. |
| FUN-002 | Each registered source MUST satisfy the provenance fields required by its current source-record contract. | Validate the Module 01 source record against the field names, fixed values, and commit format defined in the functional brief. |
| FUN-003 | The system MUST externalize AI-generated concept interpretations as candidate proposals before they can become accepted knowledge. | Run a concept-ingest fixture and confirm that a proposal exists before canonical state changes. |
| FUN-004 | The system MUST compare a proposed concept with accepted concepts before creating a new canonical concept. | Exercise a fixture containing an existing equivalent concept and inspect the reconciliation result. |
| FUN-005 | The system MUST expose a detected duplicate candidate for semantic review. | Run the curated duplicate fixture and inspect the proposal's duplicate finding. |
| FUN-006 | The system MUST expose detected ambiguity for semantic review. | Run the curated ambiguity fixture and inspect the proposal's ambiguity finding. |
| FUN-007 | The system MUST expose a detected contradiction for semantic review. | Run the curated contradiction fixture and inspect the proposal's conflict finding. |
| FUN-008 | The system MUST express accepted semantic links using relation types from the supplied course vocabulary. | Validate accepted relations against the current course relation schema. |
| FUN-009 | The system MUST identify the prerequisite marked as required by a curated missing-prerequisite fixture when it is absent from accepted concepts. | Run the fixture and compare the proposed prerequisite identifier with the fixture expectation. |
| FUN-010 | The system MUST preserve an explicit add-or-defer decision for each accepted missing-prerequisite finding. | Apply one curated add case and one curated defer case and inspect the retained decisions. |
| FUN-011 | The system MUST preserve an accepted unresolved learning gap as a question record. | Apply the curated unresolved-gap fixture and inspect the canonical question record. |
| FUN-012 | An evidence-grounded answer MUST identify the accepted source records used to support its externally verifiable statements. | Run a curated question with an expected statement-to-source map and compare the returned citations. |
| FUN-013 | An unsupported question MUST produce an explicit insufficient-evidence status. | Run the curated unsupported-question fixture and inspect the normalized result status. |
| FUN-014 | An insufficient-evidence result MUST NOT present an unsupported factual answer as established. | Inspect the normalized answer field for the curated unsupported-question fixture. |
| FUN-015 | The system MUST provide an inspectable graph view of accepted concepts and relations. | Build the graph view from a fixture vault and compare its concept identifiers and typed edges with canonical records. |
| FUN-016 | The system MUST apply the same provenance and change-control contract to the required bounded personal extension as to the shared course path. | Run one non-sensitive extension fixture through the ordinary proposal and acceptance workflow. |

## Authority and change-control requirements

These requirements keep model assistance, machine-checkable enforcement, and human semantic authority separate.

| ID | Requirement | Planned verification |
|---|---|---|
| GOV-001 | An AI-generated change MUST exist as a candidate artifact before any related canonical mutation. | Attempt application without a candidate and verify refusal with unchanged output. |
| GOV-002 | The workflow contract MUST reserve semantic approval authority for the student. | Inspect the role contract, student-operated decision evidence, and either the agent-path evidence that the AI edited only the candidate or the instructor-accepted manual fallback with no AI-authorship claim. |
| GOV-003 | Structural validation MUST NOT change canonical state. | Hash the accepted output path before and after validation. |
| GOV-004 | Structural validation MUST NOT create an approval decision. | Inspect the decision path before and after validation. |
| GOV-005 | Structural validation success MUST NOT be represented as proof of semantic correctness. | Inspect validator output and confirm that the student performs a separately recorded semantic review. |
| GOV-006 | A student decision MUST explicitly approve or reject a named proposal. | Inspect the decision artifact produced by each decision path. |
| GOV-007 | A decision MUST be bound to a SHA-256 digest of the exact proposal content reviewed by the student. | Compare the recorded digest with an independently computed digest of the proposal. |
| GOV-008 | Changing proposal content after a decision MUST invalidate that decision for application. | Modify a decided proposal and verify that `apply` refuses it. |
| GOV-009 | Absence of a decision artifact MUST prevent application. | Attempt `apply` without the decision file and verify unchanged output. |
| GOV-010 | An incomplete decision artifact MUST prevent application. | Remove one required decision field and verify that `apply` refuses it. |
| GOV-011 | A decision whose status is not `approved` MUST prevent application. | Exercise pending and rejected decision fixtures and verify unchanged output. |
| GOV-012 | A decision that identifies or digests a different proposal MUST prevent application. | Exercise proposal-identifier and proposal-digest mismatch fixtures and verify unchanged output. |
| GOV-013 | Application MUST write only content authorized by the matching approved decision. | Compare the accepted output with the approved proposal and decision. |
| GOV-014 | A completed canonical knowledge application MUST produce a verification result that references the applied change. | Inspect the normalized post-application result and its proposal and decision identifiers. |

## State and provenance requirements

The system uses different state classes for different meanings. These requirements define canonical ownership without selecting the internal component architecture.

| ID | Requirement | Planned verification |
|---|---|---|
| STA-001 | The student-owned external Markdown vault MUST be the canonical knowledge store. | Trace the Module 01 source record, and later concept and question fixtures, to ordinary Markdown files in the external vault. |
| STA-002 | A canonical source record MUST preserve primary material or a version-resolving reference to it. | Resolve the Module 01 `course_path` at its recorded 40-character `course_commit`. |
| STA-003 | A canonical concept record MUST preserve the accepted interpretation defined by the current concept schema. | Inspect the normalized fields of an approved concept fixture. |
| STA-004 | A canonical concept relation MUST preserve its accepted type and endpoint identifiers. | Compare an approved relation fixture with the canonical Markdown record. |
| STA-005 | A canonical question record MUST preserve an explicit unresolved gap defined by the current question schema. | Inspect the normalized fields of an approved unresolved-gap fixture. |
| STA-006 | Proposal, decision, and operation-log records MUST use artifact classes distinct from semantic source, concept, and question records. | Validate every artifact in one accepted fixture change against its declared record type. |
| STA-007 | Derived embeddings, indexes, compiled graphs, caches, and exports MUST be rebuildable from controlled definitions and canonical vault state. | Delete the derived fixture output, rebuild it with the same controlled versions, and compare the expected record identifiers, relation edges, and retrieval fixture results. |
| STA-008 | A derived artifact MUST NOT become the only retained copy of accepted knowledge. | Remove the derived fixture output and confirm that all accepted records remain in canonical Markdown. |
| STA-009 | The external vault MUST remain outside the course Git repository. | Inspect repository status after vault initialization and confirm that no vault path is tracked. |
| STA-010 | The external vault MUST remain outside the mandatory submission bundle. | Compare the submitted paths with the Laboratory 01 evidence manifest. |

## Quality, privacy, and operability requirements

The following requirements constrain how the mandatory course path behaves under failure, change, and ordinary student use.

| ID | Requirement | Planned verification |
|---|---|---|
| QUA-001 | A deterministic validation operation MUST return the same structural result for the same controlled input and validator version. | Repeat validation without changing inputs and compare normalized results. |
| QUA-002 | A refused or failed operation MUST leave its accepted output unchanged. | Hash the accepted fixture output before and after each negative test. |
| QUA-003 | Every accepted semantic knowledge change MUST be traceable to its source evidence, proposal, student decision, and application result. | Resolve all four references for one accepted fixture change. |
| QUA-004 | Every project-owned normative or executable artifact MUST be version-controlled. | Compare the supplied requirements, schemas, commands, policies, and public tests with the Git tree at the submitted commit. |
| QUA-005 | Deterministic acceptance tests MUST run without consuming model quota. | Run the deterministic suite with model access disabled. |
| QUA-006 | Canonical contracts MUST remain independent of one model family, provider API, or agent harness. | Inspect each mandatory canonical schema and confirm that no model, provider, or harness field is required to validate an otherwise complete fixture. |
| QUA-007 | The mandatory path MUST NOT require purchase of a paid model subscription, prepaid API balance, separately billed model use, or paid cloud infrastructure. A no-cost account MAY require provider-side payment-card verification, but card data MUST remain outside project artifacts and submitted evidence. | Inspect mandatory setup and execution instructions, confirm that every required path can run without a charge or purchase, and confirm that no card data is requested in project commands or evidence. |
| QUA-008 | The mandatory path MUST NOT require private personal data. | Complete all shared acceptance cases using course and synthetic fixtures only. |
| QUA-009 | Credentials and authentication state MUST remain outside version-controlled project artifacts and submitted evidence. | Scan the submitted Git tree and evidence manifest for credential files, tokens, and authentication-state files. |
| QUA-010 | Submitted logs, reports, and screenshots MUST NOT contain credentials, tokens, or authentication secrets. | Scan submitted text and images for credentials, tokens, and authentication secrets. |
| QUA-011 | The external vault MUST remain readable as ordinary Markdown without Obsidian. | Open the Module 01 source record with a plain text reader while Obsidian is unavailable. |
| QUA-012 | Loss of derived runtime state MUST be recoverable without changing canonical knowledge. | Delete and rebuild the derived fixture while comparing canonical-file hashes before and after recovery. |
| QUA-013 | Submitted screenshots MUST show host and user identity sufficient to attribute the workstation, including an absolute path or operating-system account where those appear in the captured interface. | Inspect the screenshot set and reject a set that could belong to an anonymous machine. |

## Laboratory 01 acceptance boundary

Laboratory 01 sets up the workspace and checks the first authority boundary. It does not implement the rest of the system. The rows below are the observable results of this laboratory only.

The Laboratory 01 evidence manifest is fixed so that `L01-016`, `STA-010`, and the credential requirements have an observable submission boundary. It consists of `reports/lab01/REPORT.md`, `environment-report.json`, `provision.log`, `boundary-proposal.yaml`, `boundary-decision.json`, `student/design/learning-system-boundary.yaml`, selected files under `reports/lab01/screenshots/`, and the submitted fork URL, branch name, and complete commit hash. The external vault directory is not copied into this manifest. Screenshots may show vault files, absolute paths, and the operating-system account; they remain the instructor-visible evidence for source registration and workstation attribution.

| ID | Requirement | Planned verification |
|---|---|---|
| L01-001 | The student MUST create a reproducible supported project environment that passes the supplied public checks. | Run the environment doctor and public test suite and preserve their results. |
| L01-002 | The `origin` remote MUST identify the student's fork. | Compare `git remote -v` with the submitted fork URL. |
| L01-003 | The `upstream` remote MUST identify `https://github.com/sobol-mo/ai-systems-design-course`. | Compare `git remote -v` with the required public-course URL. |
| L01-004 | Laboratory work MUST be committed on a personal branch other than `main`. | Inspect the submitted branch name and commit. |
| L01-005 | The submitted laboratory commit MUST change only paths under `training-project/student/` and `training-project/reports/`. | List the paths changed by the submitted commit and reject every path outside those two prefixes. |
| L01-006 | The student MUST create the initially absent `student/design/`, `reports/lab01/`, and `reports/lab01/screenshots/` paths through non-empty laboratory artifacts. | Inspect the submitted Git tree at the identified commit. |
| L01-007 | The student MUST initialize a student-owned external Markdown vault outside the Git clone. | Inspect submitted screenshots of the vault `README.md` and verify that the vault is absent from Git status. |
| L01-008 | The student MUST register the Module 01 theory as `sources/module-01-ai-engineering-foundations.md` in the external vault. | Validate its front-matter fields from the submitted screenshots and resolve its `course_path` at the recorded `course_commit` in the submitted fork according to the functional brief. |
| L01-009 | Laboratory 01 MUST NOT materialize structured concept records, graph indexes, or vector indexes. | Confirm from submitted screenshots and the project tree that the vault has no `concepts/` files and the project has no generated graph or vector-index output. |
| L01-010 | The proposal operation MUST edit only `reports/lab01/boundary-proposal.yaml`; when no existing agent path can complete the local operation within available access and quota without a new purchase, the student MAY use an instructor-accepted manual fallback and MUST record the attempted or unavailable path and any available sanitized failure evidence without claiming AI authorship. | Inspect the proposer-session evidence on the agent path, or inspect and accept the manual-fallback justification and available failure evidence, then compare the resulting candidate with the submitted Git state. |
| L01-011 | Structural validation MUST succeed without creating a decision or accepted boundary. | Run `validate`, inspect the decision and accepted-output paths, and preserve the refused premature-apply result. |
| L01-012 | The student MUST complete the supplied semantic review questions before approval. | Inspect the student's answers and conclusion in `REPORT.md`. |
| L01-013 | The student decision MUST record approval of the exact proposal identifier and SHA-256 digest. | Compare `boundary-decision.json` with the proposal identifier and an independently computed proposal digest. |
| L01-014 | `apply` MUST generate the accepted boundary only from the matching approved decision. | Exercise the accepted path and compare `learning-system-boundary.yaml` with the proposal and decision. |
| L01-015 | The `personal_domain` field in the accepted boundary MUST describe only a non-sensitive candidate area for later extension. | Compare the accepted boundary with `SYS-001` and `SYS-004`. |
| L01-016 | The student MUST submit every item in the Laboratory 01 evidence manifest individually rather than as an archive. | Compare the Microsoft Teams submission and the identified Git commit with the fixed evidence manifest. |

## Constraint traceability summary

This summary introduces no additional obligations. It helps reviewers locate the normative requirement that controls each important exclusion:

- requirements elicitation or replacement as student work is excluded by `SYS-007`;
- application-architecture design in Laboratory 01 is excluded by `SYS-008`;
- premature concept, graph-index, and vector-index materialization is excluded by `L01-009`;
- replacing the fixed learning-system identity with a personality model or general personal knowledge system is excluded by `SYS-001` and the functional brief;
- AI semantic approval authority is excluded by `SYS-003` and `GOV-002`;
- provider or harness details as mandatory canonical-contract fields are excluded by `QUA-006`;
- a derived graph or index as the only retained knowledge copy is excluded by `STA-008`;
- private personal data as mandatory input is excluded by `QUA-008`;
- credentials and authentication secrets in evidence are excluded by `QUA-010`;
- foundation-model training from scratch is excluded by `SYS-009`;
- high-consequence medical, financial, legal, and safety-critical decision outcomes are excluded by `SYS-010`.

The organization constraints of the vault structure contract are fixed by the supplied contract rather than repeated here: folders represent record type rather than subject domain, domain grouping uses faceted tags, and meaning-bearing connections use typed relations rather than folder trees or tags.

## Known Laboratory 01 enforcement limit

Laboratory 01 records the student's identifier in `recorded_by`, but the command does not authenticate the person operating it. `GOV-002` is therefore a workflow-authority and evidence requirement at this stage: the student operates `decide`; on an agent path, proposer-session evidence shows that the AI edited only the candidate and did not invoke `decide` or `apply`; on the instructor-accepted manual fallback, the report records that the student authored the candidate, the attempted or unavailable path, and any available sanitized failure evidence. The fallback demonstrates artifact control but not live AI/student actor separation. The baseline does not claim technical actor-identity enforcement. A later reviewed agent architecture may introduce stronger attestation or access control.

## Assumptions and unresolved inputs

This draft depends on inputs that must remain visible until the instructor resolves or supplies them. They are not silently converted into requirements:

1. A separate authoring session will define and review the supplied reference architecture before a laboratory depends on it.
2. The fixed typed-relation vocabulary and its positive and negative examples will be finalized before relation validation becomes a student requirement. Examples of relation names in the vault structure contract are pedagogical, not that vocabulary.
3. Numeric quality thresholds for retrieval, grounded answers, latency, and cost will be introduced with representative evaluation evidence rather than invented in this baseline.
4. The minimal Laboratory 01 source-record path and fields are fixed in the functional brief; the root vault directories, tag convention, and folder invariants are fixed in the vault structure contract. Later source, concept, relation, question, and knowledge-operation schemas are not invented here.

## Review gate

This baseline remains `Work in Progress` until the course instructor confirms that the obligations express the intended fixed system without prescribing an unreviewed architecture. Later architecture and laboratory artifacts must trace back to these identifiers or record an explicit instructor-approved change to the baseline.
