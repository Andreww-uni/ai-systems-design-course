# Module 02: Foundation Models and AI Application Architecture — Laboratory

> **Status:** Ready for Students — English laboratory re-approved after report-packaging alignment on 2026-09-19

## Goal

Build one governed, model-backed concept-proposal operation for the supplied learning knowledge system and prove where deterministic control ends and human authority begins. The student registers the exact Module 02 theory fragment as a source, exercises three deterministic offline fixtures, obtains two live structured responses to the same bounded request, imports and validates the resulting candidates, compares the two live runs, reviews and selects one candidate, records a digest-bound decision, applies it once under controlled rules, demonstrates that a repeated application refuses without changing accepted state, and preserves machine-readable and visual evidence of the whole chain.

The completed laboratory produces one observable result: a provider-neutral canonical concept `Structured Output` that descends from a live response, is bound by SHA-256 digests through validation, review, decision, and application, and is confirmed by a passing final verifier. The three offline fixtures demonstrate that parseable syntax, deterministic invariants, and semantic acceptance are distinct gates; the two live runs demonstrate run variability or fallback portability; the refusal demonstrates that accepted state cannot be overwritten outside the controlled workflow.

## Expected competencies

After completing the laboratory, the student can:

- distinguish the syntactic gate, the deterministic invariant gate, and the semantic acceptance gate of a structured-output operation;
- explain why provider-side schema enforcement cannot replace deterministic invariant validation or human semantic review;
- register an exact, version-bound source fragment and prepare a byte-identical, provider-neutral model request from it;
- obtain a live structured response through the primary Antigravity CLI path or the verified OpenRouter free contingency without committing credentials;
- import a raw response into an immutable, evidence-bound candidate proposal while keeping transport-specific fields out of canonical records;
- interpret a two-run comparison as same-model variability or fallback portability rather than attributing every difference to sampling;
- record a semantic review and an explicit decision that bind the exact candidate digest, and apply that candidate only once under the write-once rules;
- preserve evidence without publishing credentials, payment-card data, or unrelated private vault content.

## Prerequisites

Complete this laboratory independently before the scheduled session. The session is reserved for demonstrating the result, answering the control questions, and discussing design decisions. The course laboratory standing rules in [`LABORATORY_STANDING_RULES.md`](../../LABORATORY_STANDING_RULES.md) apply to this laboratory.

The required starting conditions are:

- Module 02 theory material has been studied, especially the three control gates in §1.3 and the model-backed concept-proposal operation;
- Laboratory 01 is complete, so the student already has a fork with `origin` and `upstream`, a personal branch, a working `training-project` environment, and an external Markdown vault containing `README.md` and `sources/module-01-ai-engineering-foundations.md`;
- the workstation satisfies the Laboratory 01 capability requirements (Git, GitHub CLI, `uv`, and Obsidian);
- an agent path is available for the two live responses: Antigravity CLI as the primary path, or an OpenRouter free profile as the verified contingency when AGY quota is unavailable or exhausted.

The mandatory path does not require purchasing model API access. A no-cost student account may require provider-side payment-card verification; card data must never enter the project, the report, or submitted evidence. The OpenRouter free profile may change or lose free availability over time; the laboratory uses the currently verified profile without claiming that free availability is permanent. Record the actual model and adapter used in `REPORT.md`.

## Starting state

The student begins with the completed Laboratory 01 fork and external vault. The vault contains `README.md` and `sources/module-01-ai-engineering-foundations.md`; it does not yet contain `concepts/structured-output.md`. The Laboratory 01 proposal, decision, and accepted boundary remain unchanged and stay outside the Laboratory 02 digest chain.

Before the first Laboratory 02 command, synchronize the published course state and create a personal branch so upstream-owned files stay current and laboratory work stays on the student branch:

```powershell
git switch main
git fetch upstream
git merge upstream/main
git push origin main
git switch -c lab02/<student-id>
```

A student who has not yet published Laboratory 01 should first complete and push that work; the synchronization above must not discard unpublished work.

The same clone supplies the fixed source and the executable workflow. The registered source is the complete `### 1.3 Structured output controls syntax, not meaning` subsection of the Module 02 theory, identified as `module-02-1-3-structured-output-controls-v1`. The CLI, candidate schema, and public tests are upstream-owned; the student reads and runs them but does not edit them. Student work is committed only under `training-project/reports/` and `training-project/student/` and pushed only to `origin`.

The external vault is student-owned and lives **outside** the clone. The student resolves its absolute path once per terminal session into a shell variable and passes it through `--vault` on every vault-aware command:

```powershell
$vault = "C:\absolute\path\to\ai-systems-learning-vault"
```

```bash
vault="/absolute/path/to/ai-systems-learning-vault"
```

The CLI refuses a vault located at or below the course clone. The path is not stored in any project configuration file, is not a credential, and the complete vault is never attached to the submission.

The artifact tree is fixed by the approved contract:

```text
reports/lab02/
  REPORT.md
  live-comparison.json
  semantic-review.yaml
  verification-report.json
  submission/
    REPORT.md                 (generated Teams copy with embedded images)
  revisions/                  (only when a human revision is used)
  reviews/                    (only when a candidate is rejected)
  runs/<run-id>/
    model-request.json
    raw-response.txt
    run-metadata.json
    validation-result.json
  screenshots/
    01-offline-gates.png
    02-refusal-unchanged.png
    03-live-comparison.png
    04-review-decision.png
    05-controlled-apply.png
    06-final-result.png

<external-vault>/
  sources/module-02-foundation-models-and-ai-application-architecture.md
  proposals/lab02-structured-output-<run-id>.md
  decisions/lab02-structured-output-<run-id>-decision.md
  operations/lab02-structured-output-<run-id>-apply.md
  concepts/structured-output.md
```

The numbered steps show Windows PowerShell because that is the primary documented path. Linux and macOS substitute POSIX directory commands (`cd`) and POSIX line continuation (`\`); Git, `uv`, and `learning-project` argument values are otherwise the same. Do not translate a Windows-only installer into an unreviewed Linux or macOS command.

## Steps

### Step 1: Register the Module 02 source

From the `training-project` directory, register the exact source fragment against the current clone commit. The registration is preparation, not a governed semantic change.

```powershell
cd "$HOME\projects\ai-systems-design-course\training-project"
git -C .. rev-parse HEAD
uv run learning-project lab02 register-source --vault "$vault" --course-root .. `
  --theory ../modules/02_Foundation_Models_and_AI_Application_Architecture/02_Foundation_Models_and_AI_Application_Architecture_Theory.md `
  --course-repository "$(git remote get-url origin)" --course-commit "$(git rev-parse HEAD)" --by "<student-id>"
```

Linux and macOS use `cd` and line continuation with `\`; the argument values are identical.

`register-source` writes `sources/module-02-foundation-models-and-ai-application-architecture.md` in the vault and records the source identifier, the exact course path, the repository, the clone commit, and the SHA-256 digest of the complete §1.3 fragment. Re-running it against the same bytes is a no-op; registering a different commit or different content for the same source identifier is refused rather than silently overwriting the record.

The captured `course_commit` is the immutable source baseline, not the later submission commit. The final verifier requires that this commit exists and is an ancestor of `HEAD`, then compares upstream-owned paths against that baseline. Student-owned `training-project/reports/` and `training-project/student/` paths may still change and be committed later. Do not re-register the source after committing the report: that would change the bound chain.

**Expected result:** the vault contains the new source record with `source_id: module-02-foundation-models-and-ai-application-architecture`, one `fragments` entry with `fragment_id: module-02-1-3-structured-output-controls-v1` and a `fragment_sha256`, and the exact clone commit captured by `git rev-parse HEAD`.

### Step 2: Exercise the offline fixtures

Initialize the source report and screenshot directory before capturing the first checkpoint. The report starts from the supplied Ukrainian template, retains relative image links throughout verification, and is not replaced on a later run:

```powershell
New-Item -ItemType Directory -Force .\reports\lab02\screenshots | Out-Null
if (-not (Test-Path .\reports\lab02\REPORT.md)) { Copy-Item .\fixtures\lab02\REPORT.md .\reports\lab02\REPORT.md }
```

On Linux or macOS, use `mkdir -p reports/lab02/screenshots` and `test -f reports/lab02/REPORT.md || cp fixtures/lab02/REPORT.md reports/lab02/REPORT.md`.

Then run the read-only fixture check. It executes the three approved deterministic substitutes in temporary state, never touching the vault or the accepted concept.

```powershell
uv run learning-project lab02 check-fixtures --vault "$vault"
```

The three fixtures exercise three different gates:

1. `valid-response.json` is a structurally valid candidate that passes the syntactic and deterministic gates;
2. `malformed-response.txt` is not one valid JSON value and is refused at the syntactic gate before any proposal record is created;
3. `semantic-unsupported-response.json` is structurally valid and passes deterministic gates, but its definition and quotations must still be judged by the authorized human reviewer at the semantic acceptance gate.

**Expected result:** the command prints a normalized summary naming the valid, malformed, and semantically unsupported fixtures and confirming that accepted state is unchanged. Capture the terminal output as `reports/lab02/screenshots/01-offline-gates.png`; the normalized fixture summary, the operating-system account or GitHub login, and the system date must be visible in the image. Do not capture `02-refusal-unchanged.png` here; that checkpoint is taken after the successful apply in Step 10.

### Step 3: Prepare the first live request

Prepare the first live run. `prepare` reads the registered source and writes a byte-identical, provider-neutral request that embeds the exact fragment and declares source-only and exact-quotation constraints.

```powershell
uv run learning-project lab02 prepare --vault "$vault" --report-dir reports/lab02 --run-id live-primary-01
```

The request contains `request_id: lab02-structured-output-v1`, `operation: create`, `target_concept_id: structured-output`, the exact fragment text and digest, and `constraints` that prohibit external knowledge and require exact source quotations. The same command for a second run identifier writes identical request bytes, which the later comparison depends on.

**Expected result:** `reports/lab02/runs/live-primary-01/model-request.json` exists and is the only file in that run directory.

### Step 4: Obtain the first live response

Use the primary AGY path when its quota is available. Select a model from the authenticated account's available list:

```powershell
agy models
uv run learning-project lab02 run-agy --report-dir reports/lab02 --run-id live-primary-01 `
  --model-id "<model-from-agy-models>" --by "<student-id>"
```

`run-agy` invokes Antigravity CLI with the exact prepared request and the candidate schema, extracts the structured response from the AGY result envelope, writes only the response to `raw-response.txt`, and records `run-metadata.json` with `evidence_kind: live`, `adapter: agy`, the selected `model_id`, and the run attribution. It refuses a response that is not one single JSON object or that does not finish successfully, without leaving partial run evidence.

If AGY quota is unavailable or exhausted, use the verified OpenRouter free contingency. Obtain a key at https://openrouter.ai/settings/keys, keep it out of the repository, and never send it in chat. Provide it to the command only through the process environment. On Windows, mask the prompt and convert the value only into that session's environment:

```powershell
$secure = Read-Host "OpenRouter API key" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
Remove-Variable secure, bstr
uv run learning-project lab02 run-openrouter --report-dir reports/lab02 --run-id live-primary-01 --by "<student-id>"
Remove-Item Env:OPENROUTER_API_KEY
```

On Linux or macOS, read the key without echoing it, export it only for the following command, then unset it:

```bash
read -s OPENROUTER_API_KEY
export OPENROUTER_API_KEY
uv run learning-project lab02 run-openrouter --report-dir reports/lab02 --run-id live-primary-01 --by "<student-id>"
unset OPENROUTER_API_KEY
```

`run-openrouter` uses the pinned free profile `nex-agi/nex-n2.5-mini:free`, reads the key only from `OPENROUTER_API_KEY`, enforces a 120-second overall deadline, and records `adapter: openai-compatible`. The key never appears in arguments, run metadata, or submitted evidence. Free model availability may change; if the profile is no longer available, report the limitation and use AGY.

**Expected result:** `reports/lab02/runs/live-primary-01/raw-response.txt` contains exactly one JSON candidate and `run-metadata.json` records the live adapter and the model actually used. `git status` does not show the key, and no key value appears in any artifact.

### Step 5: Import and validate the first candidate

Import the raw response into an immutable, evidence-bound proposal, then run deterministic validation.

```powershell
uv run learning-project lab02 import --vault "$vault" --report-dir reports/lab02 --run-id live-primary-01 --evidence-kind live
uv run learning-project lab02 validate --vault "$vault" --report-dir reports/lab02 `
  --proposal-id lab02-structured-output-live-primary-01 `
  --output reports/lab02/runs/live-primary-01/validation-result.json
```

`import` preserves the exact raw response bytes, binds the request and response digests and the source and fragment identifiers into the proposal, and normalizes only the closed candidate fields into the proposal body. Any transport-specific field present in the harness response is removed from the proposal so canonical records remain provider-neutral. `validate` checks representation syntax, required fields, identifiers, allowed values, the three source-support categories in the declared order, and that every quotation is an exact substring of the registered fragment.

A passing `validate` result proves that the candidate is syntactically and deterministically well formed. It does not prove that the definition is correct or that each quotation actually supports its claim; that judgment belongs to the semantic acceptance gate in Step 8.

**Expected result:** the vault contains `proposals/lab02-structured-output-live-primary-01.md`, and `validation-result.json` records `valid: true` with passing syntactic and invariant gates. If `valid` is false, read the reported errors, obtain a new live response under a new run identifier, and repeat import and validation; do not edit the raw response or the proposal in place.

### Step 6: Prepare and obtain the second live response

Repeat Steps 3–5 for a second run identifier. Prefer the same adapter and model as the first live run. Using the same model demonstrates run-to-run variability; using a different model or adapter because AGY quota ran out demonstrates fallback portability. The later comparison reads adapter and model from run metadata; do not relabel a contingency run as same-model variability.

```powershell
uv run learning-project lab02 prepare --vault "$vault" --report-dir reports/lab02 --run-id live-primary-02
```

If the first live run used AGY and quota remains:

```powershell
uv run learning-project lab02 run-agy --report-dir reports/lab02 --run-id live-primary-02 `
  --model-id "<model-from-agy-models>" --by "<student-id>"
```

If Step 4 already used OpenRouter, or AGY quota is now unavailable, repeat the same OpenRouter environment sequence as Step 4, then:

```powershell
uv run learning-project lab02 run-openrouter --report-dir reports/lab02 --run-id live-primary-02 --by "<student-id>"
```

Then import and validate the second candidate:

```powershell
uv run learning-project lab02 import --vault "$vault" --report-dir reports/lab02 --run-id live-primary-02 --evidence-kind live
uv run learning-project lab02 validate --vault "$vault" --report-dir reports/lab02 `
  --proposal-id lab02-structured-output-live-primary-02 `
  --output reports/lab02/runs/live-primary-02/validation-result.json
```

The second request must be byte-identical to the first. Keep the actual adapter and model in the run metadata and reflect them honestly in the later comparison and report.

**Expected result:** two distinct run directories exist with two live raw responses, two `run-metadata.json` records whose `request_sha256` values are identical, and two validation results. Both candidates descend from live responses rather than fixtures.

### Step 7: Compare the two live runs

Compare the two runs. The comparison classifies them from the recorded adapter and model, not from a manual guess.

```powershell
uv run learning-project lab02 compare-live --vault "$vault" --report-dir reports/lab02 --run-id live-primary-01 live-primary-02
```

The command writes `reports/lab02/live-comparison.json`. When both runs used the same adapter and model, `comparison_kind` is `same-model-variability`. When one run used a different model or access path, it is `fallback-portability`. The comparison records the shared request digest, both run digests, both proposal digests, and deterministic structural differences.

**Expected result:** `live-comparison.json` identifies the two run identifiers, their adapter and model paths, the shared request digest, and the correct `comparison_kind`. Capture this evidence as `reports/lab02/screenshots/03-live-comparison.png`; the two run identifiers, adapter and model paths, comparison result, operating-system account or GitHub login, and system date must be visible. A contingency path must be visibly labeled rather than presented as pure same-model variability.

### Step 8: Review and select one candidate

Select one acceptable candidate, then write the semantic review. Begin only after the selected candidate passes deterministic validation. The command examples below use `live-primary-01`. If the selected candidate is run 02, a later live generation, or a human revision, replace every later `proposal-id`, validation path, review path, and apply path with that candidate's identifiers.

Use these paths consistently:

- a live run `<run-id>` has proposal `lab02-structured-output-<run-id>` and validation `reports/lab02/runs/<run-id>/validation-result.json`;
- a human revision `<revision-id>` has proposal `lab02-structured-output-<revision-id>` and validation `reports/lab02/revisions/<revision-id>/validation-result.json`;
- `reports/lab02/semantic-review.yaml` is reserved for the finally selected candidate;
- a rejected candidate keeps its own review at `reports/lab02/reviews/<proposal-id>.yaml`. Do not overwrite or copy a review that is already bound to a decision.

Read the registered source fragment, the candidate definition, the three key points, and each `source_support` entry, then answer the following questions:

1. Does the definition correctly represent `Structured Output` as the source uses the term?
2. Does each of the three exact quotations actually support its associated `claim_kind` (definition, syntax-vs-semantics, authority-boundary)?
3. Does the candidate distinguish the syntactic gate, the deterministic invariant gate, and the semantic acceptance gate without granting the first two semantic authority?
4. Does the candidate preserve the boundary that the model proposes while an authorized human reviewer decides and a separate application operation writes accepted state?
5. Does the candidate add any meaning that the source does not support?
6. Are the tags and key points useful for the learning purpose rather than provider or harness metadata?

Record the answers and the verdict in `reports/lab02/semantic-review.yaml` with the following fields:

```yaml
schema_version: "1.0"
review_id: lab02-structured-output-review
proposal_id: lab02-structured-output-live-primary-01
proposal_sha256: "<exact SHA-256 of the proposal file>"
validation_id: lab02-structured-output-live-primary-01-validation
validation_sha256: "<exact SHA-256 of the validation-result.json file>"
findings:
  definition: "<answer to question 1>"
  control_gates: "<answer to questions 2 and 3>"
  authority_boundary: "<answer to question 4>"
rationale: "<answers to questions 5 and 6, then why the candidate is acceptable or unsupported>"
verdict: acceptable
reviewed_by: "<student-id>"
```

`findings.definition` answers question 1, `findings.control_gates` answers questions 2 and 3, and `findings.authority_boundary` answers question 4. Do not add extra YAML fields. `rationale` must answer questions 5 and 6: whether the candidate adds unsupported meaning, and whether the tags and key points serve the learning purpose rather than provider or harness metadata.

Compute the two digests over the exact stored file bytes and paste the lowercase hexadecimal values. Do not invent them. Use the same command on Windows, Linux, and macOS so the case matches the workflow exactly. Pass each path as an argument; do not interpolate `$vault` inside the Python source, because Windows paths such as `C:\absolute\path\to\ai-systems-learning-vault` would then be parsed as string escapes. Run the commands from `training-project` with the vault variable already set:

```powershell
uv run python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "reports/lab02/runs/live-primary-01/validation-result.json"
uv run python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "$vault/proposals/lab02-structured-output-live-primary-01.md"
```

When another candidate is selected, replace both argument paths with that candidate's validation file and proposal file.

Set `verdict` to `acceptable` only when every question supports it; otherwise set `unsupported`, reject the candidate in Step 9, and obtain a new candidate or a human revision under the rules below. When the verdict is `unsupported`, save this review to `reports/lab02/reviews/<proposal-id>.yaml` instead of `semantic-review.yaml`; `semantic-review.yaml` is written only for the candidate that is finally applied.

If no live candidate is acceptable, correct it without editing in place. Choose one of two recovery paths before a successful `apply`.

1. Obtain another live generation under a new run identifier such as `live-retry-03`. That consumes model tokens and creates a new candidate. The two-live-response requirement remains the original compared pair from Step 7; a later generation is additional recovery, not a replacement of those two runs. Import and validate the new run, then substitute its proposal identifier and `reports/lab02/runs/live-retry-03/validation-result.json` in the later commands.

2. Write a revision input and create a new human-revised candidate. The parent proposal, raw response, and any already bound review stay immutable.

```yaml
schema_version: "1.0"
revision_id: human-01
derived_from:
  proposal_id: lab02-structured-output-live-primary-01
  proposal_sha256: "<exact SHA-256 of the parent proposal file>"
changes:
  definition: "<replacement definition>"
rationale: "<why this correction is required>"
revised_by: "<student-id>"
```

`derived_from.proposal_id` and `derived_from.proposal_sha256` are required. `changes` may replace only `definition`, `key_points`, `source_support`, and `tags`. Then:

```powershell
uv run learning-project lab02 revise --vault "$vault" --revision reports/lab02/revisions/human-01.yaml
uv run learning-project lab02 validate --vault "$vault" --report-dir reports/lab02 `
  --proposal-id lab02-structured-output-human-01 `
  --output reports/lab02/revisions/human-01/validation-result.json
```

The revised candidate is a new candidate. A decision on the parent proposal never authorizes it. Repeat semantic review into `reports/lab02/semantic-review.yaml` only for the candidate that will be applied.

A human revision is not a third live run and does not change `compare-live` classification, which still reads adapter and model metadata from the two compared live runs.

**Expected result:** the semantic review exists, names the selected proposal and validation identifiers, binds both exact digests, and records a justified verdict. After recording the decision in Step 9, capture the review and decision together as `reports/lab02/screenshots/04-review-decision.png`; the semantic verdict, approved decision, matching proposal digest, operating-system account or GitHub login, and system date must be visible.

### Step 9: Record the decision and apply once

Record the explicit decision and apply only the finally selected approved candidate. If that candidate is run 02, a later generation, or a human revision, substitute its proposal identifier, validation path, and review path in every command below.

To reject an unsupported candidate, keep its review at `reports/lab02/reviews/<proposal-id>.yaml` and do not apply it:

```powershell
uv run learning-project lab02 decide --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 `
  --validation reports/lab02/runs/live-primary-01/validation-result.json `
  --review reports/lab02/reviews/lab02-structured-output-live-primary-01.yaml `
  --reject --reason "<why the candidate is unsupported>" --by "<student-id>"
```

For the selected acceptable candidate:

```powershell
uv run learning-project lab02 decide --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 `
  --validation reports/lab02/runs/live-primary-01/validation-result.json `
  --review reports/lab02/semantic-review.yaml --approve --by "<student-id>"
uv run learning-project lab02 apply --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 `
  --validation reports/lab02/runs/live-primary-01/validation-result.json `
  --review reports/lab02/semantic-review.yaml
```

`decide` refuses an approval unless the semantic review verdict is `acceptable` and binds the exact proposal, validation, and review digests. `apply` refuses unless the decision is `approved`, the candidate descends from a live response, the registered source has not changed, and the target `concepts/structured-output.md` is absent. On success it writes the accepted concept and one matching operation record. A rejected candidate must not be applied.

**Expected result:** the vault contains the selected candidate's `decisions/...-decision.md`, one `operations/...-apply.md`, and `concepts/structured-output.md`, with the accepted concept carrying `accepted_from` that binds the proposal and decision digests. Capture the concept and operation records as `reports/lab02/screenshots/05-controlled-apply.png`; the created concept and successful operation identifiers and digests, operating-system account or GitHub login, and system date must be visible.

### Step 10: Demonstrate refusal with unchanged accepted state

Run the same `apply` command a second time. It must refuse because the accepted concept already exists.

```powershell
uv run learning-project lab02 apply --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 `
  --validation reports/lab02/runs/live-primary-01/validation-result.json `
  --review reports/lab02/semantic-review.yaml
```

The command exits with an error, creates no second operation record, and leaves `concepts/structured-output.md` byte-identical. Record the digest of the concept file before and after and confirm they match. The filename `02-refusal-unchanged.png` is checkpoint 2 by contract, not by capture order; take it now, after the successful apply, not during the offline fixtures.

A full restart after a successful apply is not a reuse of `live-primary-01`. It requires a new run identifier and removal of the accepted concept and its operation record, as described in Cleanup and rollback.

**Expected result:** the repeated apply is refused with exit status 1, exactly one successful `*-apply.md` operation remains in the vault, and the accepted concept digest is unchanged. Capture this as `reports/lab02/screenshots/02-refusal-unchanged.png`; the refusal, matching before-and-after concept digest, single successful operation, operating-system account or GitHub login, and system date must be visible.

### Step 11: Prepare the report and screenshots 01–05

`lab02 verify` requires the six approved PNG files under `reports/lab02/screenshots/` and those exact filenames inside `REPORT.md`. Write the report and save screenshots `01`–`05` before running the verifier. Screenshot `06` is captured in Step 12 beside a passing result.

Complete the source report copied in Step 2. Write every section in Ukrainian, in the student's own words. Keep every supplied heading and enter the fork URL and personal branch name in the identity section. Leave the evidence commit hash blank until Step 12 creates that commit. Keep the six supplied relative Markdown image paths and short captions that include each exact filename, including `06-final-result.png`. Do not embed `data:` URIs in this source report. Explain:

- which adapter and model were used for each live run, and whether the comparison is `same-model-variability` or `fallback-portability` and why; classification follows the recorded adapter and model metadata, not whether the responses differ;
- one concrete difference between the two candidates if one exists, or an explicit statement that no difference was observed; identical correct live responses satisfy this requirement and do not prove that the model is deterministic; an observed difference under the same adapter and model does not by itself prove that sampling was the sole cause; do not spend another generation only to force a difference;
- why a passing `validate` result and a provider-side schema do not prove that a candidate is semantically correct, and which actor has authority to decide;
- what each SHA-256 binding in the chain connects and what it does not prove;
- one design trade-off among model cost, variability, provider portability, and the cost of the deterministic and human control gates;
- how credentials and payment-card data were kept out of the project and evidence, and whether the OpenRouter contingency (if used) required provider-side card verification;
- which file is canonical accepted knowledge, which files are immutable audit or run evidence, and which files are rebuildable derived results.

Place `01-offline-gates.png`, `02-refusal-unchanged.png`, `03-live-comparison.png`, `04-review-decision.png`, and `05-controlled-apply.png` under `reports/lab02/screenshots/` with those exact filenames. In every screenshot, the operating-system account or GitHub login and the system date must be visible. A report caption does not replace that visible attribution. The screenshots must not show credentials, tokens, payment-card data, authentication dialogs, unfiltered terminal history, or unrelated private vault content.

**Expected result:** `REPORT.md` exists, names all six PNG files, and screenshots `01`–`05` are present at the approved paths. Screenshot `06` is still absent; the first verify in Step 12 is expected to fail only for that reason.

### Step 12: Verify, capture the final screenshot, and submit

Run the read-only final verifier from `training-project`:

```powershell
uv run learning-project lab02 verify --vault "$vault" --report-dir reports/lab02
```

The command writes only `reports/lab02/verification-report.json` and exits `0` for a complete pass, `1` for completed verification with failed checks, or `2` when required inputs cannot be read. It verifies the registered source and fragment digest, that the source baseline commit exists and is an ancestor of `HEAD` with upstream-owned paths unchanged relative to that baseline, the three approved fixtures, the two live runs with the shared request digest, the comparison classification, the selected candidate's ancestry and validation, the semantic review and decision bindings, the accepted concept and single operation, provider-field isolation, and the six exact relative Markdown screenshot links in the source report. It refuses embedded `data:` image URIs in that source report.

The verifier checks internal consistency and attribution of live evidence but does not claim cryptographic proof that an external model performed inference, and it does not evaluate semantic correctness. A passing report proves the chain and the boundaries; it does not replace the semantic judgment recorded in Step 8.

If the first run fails only because `06-final-result.png` is missing, capture the accepted concept in Obsidian beside that command output, save it as `reports/lab02/screenshots/06-final-result.png`, and re-run the same verify command. After a passing run, recapture `06` if it does not yet show `status: passed` and exit status `0`, then re-run verify once more. The final image must visibly include the operating-system account or GitHub login and the system date as well as the accepted concept and passing result. The submitted `verification-report.json` must come from the last passing run after the final screenshot bytes exist, because the report hashes those files.

**Expected result:** `verification-report.json` reports `status: passed` with all checks passing and a nonzero artifact map, the exit status is `0`, and `06-final-result.png` shows the Obsidian concept beside that passing result.

Create an immutable evidence commit before inserting its hash into the report. If the terminal was restarted, `cd` into `training-project` first; `git add reports/lab02` is valid only there. The registered `course_commit` remains the Step 1 source baseline and must not be replaced.

```powershell
cd "$HOME\projects\ai-systems-design-course\training-project"
git status --short
git diff --check
git add reports/lab02
git commit -m "feat(lab02): govern a structured-output concept"
$evidenceCommit = git rev-parse HEAD
$evidenceCommit
```

Do not stage `modules/`, `platform/`, `fixtures/`, `tests/public/`, `schemas/`, `.venv/`, or the external vault.

Copy `$evidenceCommit` into the report field `Повний хеш коміту зі свідченнями`. The hash identifies the immutable evidence commit; it is not the hash of the later packaging commit, which cannot contain its own hash. Because this edit changes the source report bytes, run `lab02 verify` again. This must be the last passing verifier run against the source working tree:

```powershell
uv run learning-project lab02 verify --vault "$vault" --report-dir reports/lab02
uv run learning-project prepare-report .\reports\lab02\REPORT.md
```

`prepare-report` runs only after that final pass. It leaves the source report and PNG files unchanged and writes `reports/lab02/submission/REPORT.md` with the six images embedded. Open the generated file and confirm that all six figures render. The source report must still contain six relative `screenshots/...` image links and no `data:` URI; the generated copy must contain six `data:image/` entries and no local screenshot dependency.

Commit only the report identity update, the regenerated verification report, and the generated Teams copy, then push the branch to the fork:

```powershell
git add reports/lab02/REPORT.md reports/lab02/verification-report.json reports/lab02/submission/REPORT.md
git commit -m "docs(lab02): package report for submission"
git push -u origin HEAD
git status --short
```

The source report, `verification-report.json`, and generated submission report in this packaging commit now describe the same report content. Identity lives only in the report, not in the Teams assignment text field.

Do not re-run `lab02 verify` against the working tree after the packaging commit: the command rewrites `verification-report.json` with a new timestamp and would dirty the submission. To read back the submitted evidence, copy the report directory and verify the copy against the original external vault:

```powershell
$checkDir = Join-Path $env:TEMP ("lab02-submitted-verify-" + [guid]::NewGuid().ToString())
Copy-Item -Recurse reports/lab02 $checkDir
uv run learning-project lab02 verify --vault "$vault" --report-dir $checkDir
```

```bash
check_dir="$(mktemp -d)"
cp -a reports/lab02/. "$check_dir/"
uv run learning-project lab02 verify --vault "$vault" --report-dir "$check_dir"
```

Do not amend or reset either commit to chase a rewritten timestamp.

**Expected result:** the working tree is clean, the branch exists in the fork, the report identifies the immutable evidence commit, and the later packaging commit contains the source report, verification result, and self-contained Teams report without credentials, upstream-owned edits, or vault content.

## Cleanup and rollback

The external vault and project environment are cumulative course resources; a successful laboratory does not remove them. If the workflow must be repeated before submission, preserve the submitted commit, then restore only the student-owned evidence. Run identifiers are write-once, so every retry uses a new run identifier; do not delete a run directory and reuse its identifier.

Do not delete the registered source, accepted concept, or operation records as a routine response to a verifier error. A student-only report commit must not require source re-registration. Restore upstream-owned files when the verifier reports course-tree drift. Remove the accepted concept and its operation record only when restarting the governed operation completely before submission, after recording the exact digest of any already submitted commit; repeat from a new live or revision identifier, and re-register the source only if that immutable record is absent.

Do not edit a raw response, proposal, decision, bound review, or accepted concept by hand. A rejected decision must never be rewritten into an approval; obtain a new candidate or a human revision under a new identifier instead.

## Final verification

From `training-project`, run the public tests. Confirm the laboratory verifier against a disposable copy of the submitted report directory so the check does not rewrite the committed `verification-report.json`:

```powershell
uv run python -m unittest discover -s tests/public -v
$checkDir = Join-Path $env:TEMP ("lab02-submitted-verify-" + [guid]::NewGuid().ToString())
Copy-Item -Recurse reports/lab02 $checkDir
uv run learning-project lab02 verify --vault "$vault" --report-dir $checkDir
uv run learning-project prepare-report .\reports\lab02\REPORT.md
```

The self-study sequence is ready for the scheduled demonstration only when all of the following conditions are observable:

- all public tests pass;
- the three offline fixtures produce the expected gate behavior and leave the vault unchanged;
- two live runs exist with byte-identical requests and live (not fixture) metadata;
- the comparison classification matches the recorded adapters and models;
- the selected candidate passes deterministic validation, descends from a live run, and has a justified `acceptable` semantic review;
- the decision is `approved` and binds the exact candidate, validation, and review digests;
- the accepted concept and exactly one operation record exist, and a repeated apply refuses with an unchanged concept digest;
- `verification-report.json` reports `status: passed` and the command exits `0`;
- the six screenshots are present with the approved filenames and are referenced from `REPORT.md`;
- `reports/lab02/submission/REPORT.md` contains the same report with all six images embedded;
- committed paths are under `training-project/reports/` and `training-project/student/` only;
- the submitted evidence contains no credentials, tokens, payment-card data, or complete vault content.

## Submission artifacts

Follow the course laboratory standing rules in [`LABORATORY_STANDING_RULES.md`](../../LABORATORY_STANDING_RULES.md). Submit exactly these four items individually in Microsoft Teams rather than as an archive:

- `reports/lab02/submission/REPORT.md`;
- `reports/lab02/verification-report.json`;
- `reports/lab02/live-comparison.json`;
- `reports/lab02/semantic-review.yaml`.

Do not attach the six PNG files separately; they are embedded in the Teams copy and remain individually reviewable in the fork. The fork URL, branch name, and complete evidence-commit hash live only in the report identity section, not in the Teams assignment text field. Detailed run evidence remains reviewable in that immutable evidence commit; the later packaging commit contains the finalized report files. The external vault, authentication state, payment-card data, unfiltered logs, and a PDF duplicate of `REPORT.md` are excluded.

## Control questions

1. Why can syntactically valid JSON remain semantically unacceptable, and who has authority to decide?
2. How do the identifiers and SHA-256 bindings connect the reviewed candidate to the applied result, and what do they not prove?
3. What does comparison of two live runs demonstrate, and how does `same-model-variability` differ from `fallback-portability`?
