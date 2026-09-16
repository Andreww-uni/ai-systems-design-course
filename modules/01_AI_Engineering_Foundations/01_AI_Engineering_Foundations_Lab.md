# Module 01: AI Engineering Foundations — Laboratory

> **Status:** Ready for Students — English laboratory approved as part of the Module 01 English pair on 2026-09-06

## Goal

Initialize and verify the working contour for the supplied cumulative learning knowledge system: obtain the project through the required Git ownership path, reproduce the supported workstation environment, create the student-owned project areas and external Markdown vault, register the first course source, and preserve evidence of the result. A bounded, normally AI-generated system-boundary proposal then verifies the authority split without granting the agent authority to accept its own proposal. If no usable agent is available, the documented manual fallback preserves the candidate, validation, decision, and application boundaries without fabricating an agent session; it does not demonstrate live separation between AI and student actors.

The completed laboratory produces five observable results. The environment and initialized project state are the primary result; the governed proposal is a bounded verification activity within that result:

- a student GitHub fork of the public course repository, with `origin` pointing at that fork, `upstream` pointing at the instructor repository, and laboratory work confined to student-owned paths;
- a supported workstation on which the project tests and required command-line tools run reproducibly;
- student-created `student/design/` and `reports/lab01/` paths containing the required design, report, log, machine-readable, and screenshot evidence;
- a student-owned external Markdown vault containing its orientation file and the registered Module 01 theory source, whose boundary and initial protection against workstation loss can be explained;
- an accepted `learning-system-boundary.yaml` contract whose origin, human approval, and application can be verified.

## Expected competencies

After completing the laboratory, the student can:

- distinguish a working model demonstration from a controlled AI-system workflow;
- obtain course files from a personal fork rather than from instructor attachments;
- distinguish `origin` from `upstream` and distinguish upstream-owned paths from student-owned artifacts;
- reproduce the required toolchain and verify it with a second apply or a second capability check;
- distinguish reproducible infrastructure, version-controlled definitions, mutable canonical state, and rebuildable derived artifacts;
- explain the supplied learning knowledge system, register a version-resolving reference to the Module 01 theory, and keep a possible personal area as a later bounded extension rather than a different system;
- evaluate the supplied system boundary through an intended outcome, non-goals, a usefulness condition, a material risk, and a simpler non-AI baseline;
- keep AI-generated content as a proposal until deterministic validation and explicit human approval have occurred;
- preserve evidence without publishing credentials, sensitive or unrelated vault content, or unrelated workstation data.

## Prerequisites

Complete this laboratory independently before the scheduled session. The session is reserved for demonstrating the result, answering the control questions, and discussing design decisions.

The required starting conditions on every supported host are:

- the Module 01 theory material has been studied;
- the student has a GitHub account;
- a text editor and a web browser are available;
- the student can use an agent path or document why none is usable and follow the manual fallback. Antigravity CLI authenticated with a Google account is the default proposer, and a student who already has another agent subscription may use it instead.

Windows 11 is the primary documented workstation path and the majority host. A Windows student must be able to approve administrator prompts, and WinGet must be available through Windows App Installer.

Linux is an equivalent path for the same repository boundary, governed-proposal workflow, and `learning-project doctor` capability checks. It is not a second course edition. A Linux student must be able to install Git, GitHub CLI, `uv`, and Obsidian with the distribution package manager or each tool's official installer.

macOS is not a documented path in this edition. A macOS-only host is a red preflight: stop and report it instead of improvising a third workflow.

The public course repository is https://github.com/sobol-mo/ai-systems-design-course. Every laboratory file comes from a clone of the student's fork of that repository. The instructor does not attach `dsc.yaml`, the starter proposal, or other project files outside Git.

The mandatory path does not require purchasing model API access, a container runtime, a virtual machine, or Windows Subsystem for Linux. A no-cost student account may require provider-side payment-card verification; card data must never enter the project or submitted evidence. A Linux workstation is already a supported host and does not need WSL. Antigravity CLI uses the quota available to the authenticated account. A different existing agent subscription uses that subscription's quota. If no usable agent remains, use the documented manual proposal path and record the limitation honestly; do not purchase API access solely for this laboratory.

## Starting state

The student begins with an empty working folder and a GitHub account. After Step 2 the local clone is the only source of laboratory files. The workstation configuration is `training-project/fixtures/windows/lab01-workstation.dsc.yaml`. The starter proposal is `training-project/boundary-proposal.yaml`. Both files are upstream-owned: the student uses them from the clone and does not edit the upstream copies.

The same clone supplies the system definition in `training-project/requirements/SYSTEM_BRIEF.md`, the binding requirements in `training-project/requirements/REQUIREMENTS_BASELINE.md`, and the external-vault organization rules in `training-project/requirements/VAULT_STRUCTURE.md`. These files define the system every student builds. They are project inputs to read and apply, not material for requirements elicitation, replacement, or architecture invention.

The Windows workstation configuration manages Git, GitHub CLI, `uv`, and Obsidian. Linux installs the same four capabilities without applying that file. Antigravity CLI is the default proposer and is installed separately by its official installer because authentication and mutable agent state remain under student ownership. Another agent is not installed by the course configuration; the student authenticates the existing harness and points it at the same proposal file.

The numbered steps show Windows PowerShell because that is the primary documented path. Linux substitutes POSIX directory and file commands (`mkdir -p`, `cp`, `rm`) and POSIX paths (`reports/lab01/...` instead of `.\\reports\\lab01\\`). Git, `uv`, and `learning-project` commands are otherwise the same. Do not translate a Windows-only installer into an unreviewed Linux command.

The technical baseline was verified on Windows 11 25H2 with WinGet Configuration 1.29, `uv` 0.12.9, and Antigravity CLI 1.1.26. Linux is accepted at capability level: `learning-project doctor` must report a green Linux host with Git, GitHub CLI, `uv`, and Obsidian available. A later compatible release is acceptable when the commands and acceptance checks in this laboratory still behave as documented. The Windows configuration therefore declares package identities rather than unavailable historical binaries, and the project verifies capabilities after installation. This produces capability-level reproducibility rather than a bit-for-bit workstation image. Record every observed version and the proposer actually used in `REPORT.md`; do not silently replace a failed command with a different workflow.

The clone is one Git repository with two remotes. Folders are not remotes. `origin` is the student's GitHub fork and is the only remote that receives `git push`. `upstream` is the public course repository https://github.com/sobol-mo/ai-systems-design-course and is used only to fetch later instructor publications. The student never pushes to `upstream`.

The following tree is the published course layout the clone must contain. Paths marked **upstream** are maintained by the course and may be added, replaced, or deleted in a later publication; a local edit in those paths can be overwritten on the next `upstream` synchronization. Paths marked **student** do not exist until the student creates them; they are the only project paths the student commits and pushes to `origin`. Paths marked **derived** are rebuildable machine state and must not be committed.

```text
ai-systems-design-course/                  clone root
  README.md                                upstream — course navigation
  00_Curriculum.md                         upstream
  GLOSSARY.md                              upstream
  references/                              upstream
  modules/                                 upstream — theory and laboratory instructions
  training-project/                        working project
    README.md                              upstream
    pyproject.toml                         upstream
    uv.lock                                upstream
    .gitignore                             upstream
    requirements/                          upstream — supplied system definition and requirements
    boundary-proposal.yaml                 upstream starter — copy, do not edit in place
    fixtures/                              upstream — including lab01-workstation.dsc.yaml
    platform/                              upstream — CLI, doctor, and proposal workflow
    tests/public/                          upstream — public acceptance tests
    student/                               student — design and later implementation
    reports/                               student — laboratory evidence
    .venv/                                 derived — created by uv, ignored by Git
```

The external Markdown vault is student-owned and lives **outside** this tree. Obsidian is the supplied interface for opening it, but the canonical state remains ordinary Markdown files. The vault is not part of the Git repository and is not pushed to `origin`.

The laboratory distinguishes five state locations with different authority and ownership:

| State location | Authorized writer | Meaning |
|---|---|---|
| `reports/lab01/boundary-proposal.yaml` | AI on the normal path; student when correcting or using the manual fallback | Candidate content with no authority to change the accepted design |
| `reports/lab01/boundary-decision.json` | `learning-project decide` | Decision and audit evidence; the project CLI refuses to overwrite a recorded outcome |
| `student/design/learning-system-boundary.yaml` | `learning-project apply` | Accepted system-boundary contract generated only from an approved proposal; not a reference architecture |
| External Markdown vault | Student during Laboratory 01; governed workflow in later modules | Canonical learning knowledge, not project-design state |
| Upstream-owned paths listed above | Course publication workflow | Supplied contracts, course materials, project CLI, fixtures, and tests that the student reads and runs but does not edit |

Do not edit `boundary-decision.json` or the accepted contract manually. If a recorded decision must change, preserve the existing evidence, remove the generated decision and accepted contract, revise the proposal under a new `proposal_id`, and run a new review cycle.

## Steps

### Step 1: Perform a read-only preflight

On Windows, open PowerShell without administrator elevation. Do not install packages and do not clone yet. Run the following checks:

```powershell
$PSVersionTable.PSVersion
[Environment]::OSVersion.Version
winget --version
winget configure --help
```

On Linux, run a read-only host check instead of WinGet:

```bash
uname -s
cat /etc/os-release
git --version
```

Classify the result before changing the workstation:

- **green (Windows):** Windows 11, WinGet, and `winget configure` are available;
- **green (Linux):** `uname -s` reports `Linux`; Git may still be missing until the bootstrap in Step 2;
- **yellow (Windows):** WinGet exists but must be updated through Microsoft Store before configuration can be applied;
- **red:** macOS, Windows older than 11, Windows App Installer unavailable, no administrator approval on Windows, or a Linux host on which the student cannot install the required tools.

Resolve a yellow result before continuing. Stop and report a red result instead of replacing the supported path with unreviewed installation commands.

**Expected result:** a Windows host reports version `10.0.22000` or newer and both WinGet commands display version or help output without changing installed packages. A Linux host reports `Linux` and does not install packages during preflight.

### Step 2: Fork, clone, and bind remotes

Every later step reads files from this clone. The fork, the two remotes, and the personal branch are therefore part of this laboratory rather than a separate Git exercise.

Git is required before the clone. Check whether it is already present:

```powershell
git --version
```

If Git is missing on Windows, open PowerShell **as Administrator** and install only that bootstrap package:

```powershell
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
```

If Git is missing on Linux, install it with the distribution package manager. Do not apply the Windows WinGet configuration file for this bootstrap.

On Windows, close every PowerShell window and open a new non-administrator window so the updated `PATH` is loaded. Confirm `git --version` again.

Record the Git identity once on this workstation. The name and email appear on every commit:

```powershell
git config --global user.name "<student-name>"
git config --global user.email "<github-email>"
git config --global user.name
git config --global user.email
```

Create the fork in the browser, not in the terminal. Open https://github.com/sobol-mo/ai-systems-design-course, choose **Fork**, and create the copy under the student's GitHub account. Keep the repository name `ai-systems-design-course`. A fork is a separate GitHub repository the student may push to. It is not yet a folder on the workstation.

Clone **the fork**, not the instructor repository:

```powershell
New-Item -ItemType Directory -Force "$HOME\projects" | Out-Null
Set-Location "$HOME\projects"
git clone "https://github.com/<GITHUB-LOGIN>/ai-systems-design-course.git"
Set-Location .\ai-systems-design-course
git remote -v
```

Replace `<GITHUB-LOGIN>` with the GitHub account name. Linux uses `mkdir -p "$HOME/projects"` and `cd` in place of `New-Item` and `Set-Location`; the `git clone`, remote, and branch commands are the same. After this clone, Git names that fork `origin`. The output must show the student's account, not `sobol-mo`. If `origin` points at `sobol-mo/ai-systems-design-course`, the wrong repository was cloned: delete that folder and clone the fork.

Add the instructor repository as `upstream` so later course publications can be fetched. Then create a personal laboratory branch. Do not commit laboratory work on `main`.

```powershell
git remote add upstream https://github.com/sobol-mo/ai-systems-design-course.git
git remote -v
git switch -c lab01/<student-id>
git branch --show-current
```

If `upstream` already exists, verify it instead of adding it again. Use a short institutional identifier that does not expose unnecessary personal data.

The required remotes are:

```text
origin    https://github.com/<GITHUB-LOGIN>/ai-systems-design-course.git (fetch)
origin    https://github.com/<GITHUB-LOGIN>/ai-systems-design-course.git (push)
upstream  https://github.com/sobol-mo/ai-systems-design-course.git (fetch)
upstream  https://github.com/sobol-mo/ai-systems-design-course.git (push)
```

`origin` is the student's personal GitHub repository. Student-owned files are committed on the personal branch and pushed only to `origin`. `upstream` is the instructor's published course. Upstream-owned folders are updated by fetching from `upstream`, not by editing them and not by pushing to them.

Confirm that the clone contains `modules\01_AI_Engineering_Foundations\` and `training-project\fixtures\windows\lab01-workstation.dsc.yaml`. Later steps use those paths. They are not supplied as separate attachments.

When the instructor publishes an update later in the course, synchronize `main` from `upstream` and then return to the personal branch. Do not run this merge as a substitute for the first clone, and do not merge onto a dirty personal branch that contains unpublished laboratory work.

```powershell
git switch main
git fetch upstream
git merge upstream/main
git push origin main
git switch lab01/<student-id>
```

**Expected result:** `git remote -v` shows the student's fork as `origin` and `sobol-mo/ai-systems-design-course` as `upstream`; `git branch --show-current` reports `lab01/<student-id>`; `training-project\fixtures\windows\lab01-workstation.dsc.yaml` and `training-project\boundary-proposal.yaml` exist in the clone.

### Step 3: Apply the workstation configuration twice

On Windows, open PowerShell **as Administrator**, change to the `training-project` directory inside the clone, and record both configuration runs in one transcript. The configuration file is the upstream copy in the clone. Linux students skip the WinGet block and use the Linux paragraph after the Windows expected result.

```powershell
Set-Location "$HOME\projects\ai-systems-design-course\training-project"
Start-Transcript -Path .\provision.log -Force
winget configure --file .\fixtures\windows\lab01-workstation.dsc.yaml --accept-configuration-agreements
winget configure --file .\fixtures\windows\lab01-workstation.dsc.yaml --accept-configuration-agreements
winget list --id Git.Git --exact --source winget
winget list --id GitHub.cli --exact --source winget
winget list --id astral-sh.uv --exact --source winget
winget list --id Obsidian.Obsidian --exact --source winget
Stop-Transcript
```

Approve only the configuration and package-source agreements shown for that file. Do not add unrelated packages to the laboratory configuration. Do not edit `fixtures/windows/lab01-workstation.dsc.yaml`.

The first apply reconciles missing tools. The second apply checks convergence: packages already satisfying the declared state must not be reinstalled or downgraded. Keep `provision.log`; it is required evidence. Review it and remove credentials, authentication secrets, and unrelated private material before submission, but do not rewrite the configuration results. An operating-system account or absolute path may remain when it attributes the evidence to the workstation. Do not commit `provision.log` at the `training-project` root; Step 10 copies a sanitized file into `reports/lab01/`.

**Expected result:** all four package queries return an installed package. The second configuration run reports that the declared package state is already satisfied or completes without reinstalling the four tools.

Linux does not apply `fixtures/windows/lab01-workstation.dsc.yaml`. Install Git, GitHub CLI, `uv`, and Obsidian with the distribution package manager or each tool's official installer until `git --version`, `gh --version`, `uv --version`, and the Obsidian About page succeed. Run the three command-line version checks a second time; the versions must match. Save that terminal transcript as `provision.log`. On Linux, the `obsidian` executable must be on `PATH` so `learning-project doctor` can detect it. Do not edit the Windows configuration file.

On Windows, close all PowerShell windows and open a new non-administrator PowerShell so the updated `PATH` is loaded. On every supported host, verify capabilities rather than relying only on package names:

```powershell
git --version
gh --version
uv --version
```

Launch Obsidian once from the Start menu on Windows, or from the desktop entry or installed binary on Linux, and record the version shown by its About page. Obsidian is used as a Markdown vault interface; its command-line launcher is not an acceptance requirement. `learning-project doctor` must still detect the application.

### Step 4: Prepare the default proposer, another agent, or the manual fallback

Antigravity CLI is the default proposer for this year. Install it only when that is the harness the student will use. A student who already has another agent subscription skips this installer, authenticates that existing harness, and uses it in Step 7 against the same proposal file and the same `validate` / `decide` / `apply` gates.

An agent path is **usable** when an existing account or subscription can open the local `training-project`, read the required files, and complete the requested proposal edit within available quota without a new purchase. A path is unusable when authentication, account access, service availability, or quota prevents that operation. Tool preference, convenience, or reluctance to authenticate an existing account is not unavailability.

If neither the default proposer nor another existing agent subscription is usable, do not purchase API access and do not fabricate an agent transcript. Preserve a short note for the later `REPORT.md` naming the path attempted, the date, and the observed result. When the attempt produces an access, service, or quota error, retain a sanitized transcript or screenshot of that error. If the student has no existing agent account or subscription to attempt, state that fact; the laboratory does not require creating or purchasing one. Complete the documented manual path independently before the scheduled demonstration. During that demonstration, the instructor evaluates whether the justification meets the fallback admission rule; this grading decision is not a state-changing laboratory step. The deterministic gates and accepted-artifact path do not change.

On Windows, the default installer is the official user-scope Google script. Run it from a non-administrator PowerShell:

```powershell
irm https://antigravity.google/cli/install.ps1 | iex
```

This is the official Google installer script. Do not replace it with an unofficial download.

Close and reopen PowerShell, then verify the installation and begin the supported interactive authentication flow:

```powershell
agy --help
agy models
```

The first authenticated `agy` interaction is triggered when `agy models` runs; complete the browser authentication when requested. Authentication data belongs to the student and must not be copied into the repository, `provision.log`, screenshots, or the report.

Do not use `--dangerously-skip-permissions`. During the later interactive agent session, inspect every requested tool action and approve only reads of the training project and an edit to `reports/lab01/boundary-proposal.yaml`. The agent must not run `decide`, run `apply`, or edit `student/design/learning-system-boundary.yaml`, regardless of which harness is used.

**Expected result:** on an agent path, the chosen proposer can edit `reports/lab01/boundary-proposal.yaml`, while its assigned role excludes approval and application. This separation is demonstrated by the approved tool actions and preserved evidence; it is not an operating-system permission boundary. On the default path, `agy --help` displays CLI usage and `agy models` returns the models available to the authenticated account without requesting a separately billed API key. On another subscription, `REPORT.md` names that harness and `learning-project doctor` may record Antigravity CLI as unavailable. On the manual fallback, the student retains the required justification and any available sanitized failure evidence for `REPORT.md`; no proposer-session evidence is invented.

### Step 5: Initialize student-owned project and vault state

Before creating state, read `requirements/SYSTEM_BRIEF.md`, `requirements/REQUIREMENTS_BASELINE.md`, and `requirements/VAULT_STRUCTURE.md` from `training-project`. Identify the fixed system purpose, the three state boundaries, the Laboratory 01 acceptance boundary, and the minimum vault structure. These supplied contracts define the project; this step does not ask for new requirements or an application architecture.

Change to the `training-project` directory of the clone. Create the student-owned design and report directories and the initial report file, then copy the upstream starter proposal into the student report path. Do not edit `training-project/boundary-proposal.yaml` in place.

```powershell
Set-Location "$HOME\projects\ai-systems-design-course\training-project"
New-Item -ItemType Directory -Force .\student\design | Out-Null
New-Item -ItemType Directory -Force .\reports\lab01\screenshots | Out-Null
Copy-Item .\boundary-proposal.yaml .\reports\lab01\boundary-proposal.yaml
if (-not (Test-Path .\reports\lab01\REPORT.md)) { New-Item -ItemType File .\reports\lab01\REPORT.md | Out-Null }
```

Create a new external Markdown vault through the Obsidian interface. Name it `ai-systems-learning-vault` or another non-sensitive name and store it **outside** the Git clone. Add one file named `README.md` stating that the vault is student-controlled canonical learning state and is not part of the Git repository. The vault must remain usable as ordinary files without Obsidian. Obsidian may create a hidden `.obsidian/` settings directory; it is interface metadata rather than course knowledge and is not a submission artifact.

From `training-project`, obtain the exact commit that contains the theory being registered:

```powershell
git -C .. rev-parse HEAD
```

Inside the external vault, create `sources/module-01-ai-engineering-foundations.md`. Begin it with the following YAML front matter and replace the placeholder with the complete 40-character commit from the preceding command:

```yaml
---
record_type: source
source_id: module-01-ai-engineering-foundations
title: "Module 01: AI Engineering Foundations — Theory"
course_path: modules/01_AI_Engineering_Foundations/01_AI_Engineering_Foundations_Theory.md
course_commit: "<40-character Git commit>"
---
```

This record points to the exact version-controlled theory without copying it into a second editable location. It is a source registration, not a structured concept record. Do not create `concepts/`, `questions/`, `proposals/`, `decisions/`, or `operations/` directories in the vault during Laboratory 01.

Protect this mutable canonical state against loss of the workstation. On Windows, the simplest recommended baseline is to create the vault inside a directory synchronized by the student's Microsoft OneDrive account. A Linux student may use an existing equivalent off-device synchronization or backup location. Do not install or design a new backup stack for this laboratory. If no off-device protection is available, create the external vault and record that limitation honestly in `REPORT.md`.

Off-device synchronization is an initial protection measure, not a complete disaster-recovery design: an unwanted change or deletion may also be synchronized. Backup retention, monitoring, and restoration testing belong to the production-system work in Module 08.

For this laboratory, the vault proves the external system boundary and the first source registration only. Personal notes, credentials, and a full personal vault are neither required nor submitted. Record its location in `REPORT.md` as `external to repository`. A submitted screenshot may show the vault content, absolute path, or operating-system account when needed to attribute it to the workstation, but it must not show credentials, tokens, authentication secrets, or unrelated private material.

Laboratory 01 does not ingest a concept corpus or build retrieval, graph, or vector state. Those capabilities are introduced only after their theory and contracts exist in later modules.

**Expected result:** `student/design/`, `reports/lab01/screenshots/`, and `reports/lab01/REPORT.md` exist in the clone, `reports/lab01/boundary-proposal.yaml` exists as a copy, and the external Markdown vault contains its neutral `README.md` and `sources/module-01-ai-engineering-foundations.md` as the only course-required Markdown content. The source record carries the exact clone commit and course path, the vault exists outside the clone, and it does not appear in `git status`.

### Step 6: Reproduce and test the project environment

From `training-project`, create the project-local Python environment and run the public acceptance tests:

```powershell
uv sync
uv run python -m unittest discover -s tests/public -v
uv run learning-project doctor --output .\reports\lab01\environment-report.json
```

The environment under `.venv/` is derived state and is ignored by Git. Do not add it to a commit.

Before using the AI workflow, prove that a proposal cannot be accepted without a human decision:

```powershell
uv run learning-project validate .\reports\lab01\boundary-proposal.yaml
uv run learning-project apply .\reports\lab01\boundary-proposal.yaml --decision .\reports\lab01\boundary-decision.json --output .\student\design\learning-system-boundary.yaml
```

The starter file is structurally valid but contains instructional placeholders. Validation should succeed, while apply must fail because no decision exists. The `doctor` command must write a normalized environment report and return green before the AI step. Green means a supported Windows or Linux host with Git, GitHub CLI, `uv`, and Obsidian available. Authenticated Antigravity CLI is recorded when the default proposer is used; it is not required for green when another harness is used. Confirm that `student/design/learning-system-boundary.yaml` was not created.

**Expected result:** all public tests pass; the environment report records a green supported host and the four required toolchain capabilities; validation identifies a valid proposal; the premature apply exits with an error about the missing decision and creates no accepted contract.

### Step 7: Ask the AI to prepare a bounded proposal

From `training-project`, review `../modules/01_AI_Engineering_Foundations/01_AI_Engineering_Foundations_Theory.md`, especially the sections on AI use-case screening, human authority, usefulness thresholds, production risks, and simpler alternatives. Then read the local supplied contracts `requirements/SYSTEM_BRIEF.md`, `requirements/REQUIREMENTS_BASELINE.md`, and `requirements/VAULT_STRUCTURE.md`. The proposal must preserve the fixed learning knowledge system defined by those contracts. Select one non-sensitive academic or professional area only as a possible later extension recorded in `personal_domain`; it must not redefine the system or authorize personal-data ingestion.

Use an available agent when possible. Start the proposer interactively from `training-project`. The default command is:

```powershell
agy
```

A student using another agent subscription starts that harness instead. Give the same task. Do not change the proposal path, the required fields, or the later `validate` / `decide` / `apply` commands.

If Step 4 established that no agent path is usable, open `reports/lab01/boundary-proposal.yaml` in the text editor and perform the same task manually: read the named theory and supplied contracts, replace only the placeholder values, preserve every field and `status: proposed`, and do not create the decision or accepted contract. The `governance` fields describe the intended normal AI-assisted system: AI may propose, deterministic code validates, and the student decides. They do not claim that AI authored this fallback candidate. Record `manual no-agent fallback`, the attempted or unavailable path, the date, the observed limitation, and any available sanitized failure-evidence path in `REPORT.md`. Do not invent an AI explanation, chat transcript, account, or proposer screenshot.

Give the agent the following task in the interactive session:

> Read the local supplied system definition in `requirements/SYSTEM_BRIEF.md`, the applicable obligations in `requirements/REQUIREMENTS_BASELINE.md`, the vault boundary in `requirements/VAULT_STRUCTURE.md`, and the comments in `reports/lab01/boundary-proposal.yaml`. Replace only the proposal's placeholder values. Preserve the fixed learning knowledge system defined by the supplied contracts; use my selected non-sensitive academic or professional area only in `personal_domain` as a possible later bounded extension. Keep `schema_version` unchanged, keep `status: proposed`, use a new lowercase hyphenated `proposal_id`, and preserve every field. The AI may propose content but may not approve it, create a decision, run `decide`, run `apply`, or edit `student/design/learning-system-boundary.yaml`. Before editing, explain the fixed system outcome, non-goals, AI, deterministic-workflow, and human responsibilities, usefulness condition, material risk, simpler non-AI baseline, required evidence, and remaining uncertainty. Name which supplied local files support the proposal.

On an agent path, answer any domain question without supplying personal or confidential information. Inspect the explanation and the proposed diff before approving the single-file edit. End the agent session after `reports/lab01/boundary-proposal.yaml` has been updated. On the manual fallback, inspect the completed file against the same task before continuing.

**Expected result:** only `reports/lab01/boundary-proposal.yaml` changes. Its `status` remains `proposed`; it contains a bounded outcome, at least two non-goals, an explicit allocation among AI, deterministic workflow, and human authority, one testable usefulness condition, one material risk, one simpler non-AI baseline, at least two required evidence items, and one honest uncertainty. The agent path preserves proposer evidence. The manual fallback instead preserves the reason for using it and does not claim AI authorship.

### Step 8: Validate and review the proposal

Run the deterministic validator:

```powershell
uv run learning-project validate .\reports\lab01\boundary-proposal.yaml
git diff -- .\reports\lab01\boundary-proposal.yaml
```

Structural validity is necessary but does not establish semantic quality. Review the proposal using these questions:

If `validate` reports any structural error, do not run `decide`. Correct only the proposal while keeping `status: proposed`, then rerun `validate`. Begin semantic review only after validation succeeds.

1. Does the proposal preserve the supplied learning knowledge system, with `personal_domain` used only for a possible later bounded extension?
2. Does the intended learning outcome describe an observable student capability rather than “use AI”?
3. Do the non-goals prevent expansion into a complete production system or high-consequence decision process?
4. Does the responsibility allocation limit AI to proposing, assign structural enforcement to the deterministic workflow, and retain approval authority for the student? On the manual fallback, does the report distinguish this intended normal allocation from the student's authorship of the current candidate?
5. Could the usefulness condition be checked on preserved source evidence?
6. Does the risk describe a plausible failure of the complete workflow?
7. Is the non-AI baseline genuinely simpler and capable of addressing part of the outcome?
8. Do the required evidence items cover both deterministic behavior and semantic or source-grounding review?
9. Does the uncertainty identify what has not yet been established?

Record the answer and conclusion for every question in `reports/lab01/REPORT.md` before running `decide`.

If any answer is no, reject the candidate before changing it:

```powershell
uv run learning-project decide .\reports\lab01\boundary-proposal.yaml --reject --by "<student-id>" --reason "<concise reason>" --decision .\reports\lab01\boundary-decision.json
```

Preserve the rejected proposal and decision in a Git commit so the rejection remains reviewable. Then revise the proposal under a new `proposal_id`, remove only the generated decision file for the superseded review with `Remove-Item .\reports\lab01\boundary-decision.json`, and repeat validation. Never edit a recorded decision to turn rejection into approval. If the first candidate passes the semantic review, do not create an artificial rejection merely to exercise this alternative path.

**Expected result:** the final candidate passes deterministic validation and the student can justify every semantic review answer. Any rejected attempt remains explainable from Git history rather than being silently converted into an approval.

### Step 9: Record human approval and apply the contract

Only after the proposal passes both reviews, record the student's decision:

```powershell
uv run learning-project decide .\reports\lab01\boundary-proposal.yaml --approve --by "<student-id>" --decision .\reports\lab01\boundary-decision.json
uv run learning-project apply .\reports\lab01\boundary-proposal.yaml --decision .\reports\lab01\boundary-decision.json --output .\student\design\learning-system-boundary.yaml
```

The value passed through `--by` is student-supplied attribution. The project CLI requires a non-empty value but does not authenticate the operator's identity; the report, submitted Git evidence, and proposer-session evidence when applicable show that the student ran the authority-bearing commands.

Inspect the decision and accepted contract:

```powershell
Get-Content .\reports\lab01\boundary-decision.json
Get-Content .\student\design\learning-system-boundary.yaml
```

**Expected result:** the decision records `approved`, the proposal identifier, a SHA-256 digest of the exact proposal content, the student-supplied identifier, and the decision time. The accepted contract has `status: approved` and an `accepted` section linking it to the same proposal digest and recorded approval.

### Step 10: Prepare evidence and commit the result

Complete the `reports/lab01/REPORT.md` file created in Step 5. Explain, in the student's own words:

- why the selected `personal_domain` is only a possible later extension and how the intended learning outcome preserves the fixed learning knowledge system;
- why AI may be useful and what the simpler non-AI baseline can already do;
- why the normal AI-assisted system gives AI proposal authority but not approval authority and, on the manual fallback, why the student authored this candidate without changing that intended system boundary;
- the answers and conclusion for all nine semantic review questions in Step 8;
- one design trade-off involving usefulness, risk, cost, latency, privacy, or maintainability;
- whether the second workstation apply converged and any problem encountered;
- which proposer was used, or that the documented manual no-agent fallback was used, the attempted or unavailable path, the date and observed result, and any available sanitized access, service, or quota failure evidence;
- how the reproducible environment, Git-backed project artifacts, and mutable Markdown vault would each be recovered, and whether the vault currently has an off-device copy;
- why a passing schema validator does not prove that the proposal is a good system design.

Use the machine-readable `reports/lab01/environment-report.json` created by `learning-project doctor`. Do not replace it with a hand-written package list or edit a red report into a green one. Record the separate second-apply, public-test, premature-apply, and accepted-contract evidence in `REPORT.md` and screenshots.

Copy the provisioning transcript into the report directory after removing credentials, authentication secrets, and unrelated private material:

```powershell
Copy-Item .\provision.log .\reports\lab01\provision.log
```

Do not include email addresses, tokens, authentication secrets, model session files, or raw environment-variable dumps. An absolute path or operating-system account may remain when it is needed to attribute evidence to the workstation, but unrelated private paths and account data must be removed. Preserve the package and convergence output in the sanitized transcript.

Each submitted screenshot must be attributable to the student's workstation through visible operating-system context or a matching caption in `REPORT.md`. Capture screenshots that show only:

- `git remote -v` with `origin` on the student's fork and `upstream` on `sobol-mo/ai-systems-design-course`;
- the four installed workstation packages or successful capability checks; convergence is evidenced by the sanitized `provision.log`, not by a screenshot;
- the passing public tests;
- on an agent path, the proposer session with agent-service account identifiers, authentication content, and unrelated private material excluded, showing that the agent edited only `reports/lab01/boundary-proposal.yaml` and did not run `decide` or `apply`; on the manual fallback, no proposer screenshot is invented, while any genuine access, service, or quota error is submitted in sanitized form and `REPORT.md` identifies the attempted or unavailable path, date, and observed result;
- the external Markdown vault opened in Obsidian with its neutral `README.md` and the complete YAML front matter of `sources/module-01-ai-engineering-foundations.md` visible; the screenshot may show the absolute path or operating-system account to attribute the vault to the workstation, but must not show credentials or authentication secrets;
- the refused premature apply and the later accepted contract.

Review the repository state from `training-project`, then commit only student-owned laboratory artifacts. Do not stage `modules/`, `platform/`, `fixtures/`, `tests/public/`, `boundary-proposal.yaml` at the project root, `.venv/`, or `provision.log` at the project root.

```powershell
git status --short
git diff --check
git add student/design/learning-system-boundary.yaml reports/lab01
git commit -m "feat(lab01): establish governed AI system boundary"
git status --short
git rev-parse HEAD
```

Authenticate GitHub CLI, then push the personal branch to the student's fork. The push target is `origin`. It is not `upstream`.

```powershell
gh auth login
git push -u origin HEAD
```

**Expected result:** the working tree is clean after the commit, the branch exists in the student's fork, `git remote -v` still shows the required ownership, and the submitted commit contains no upstream-owned edits, `.venv/`, credentials, complete personal vault, or unrelated workstation data.

## Cleanup and rollback

The installed workstation tools and external vault are cumulative course resources, so a successful laboratory does not remove them. If the workflow must be repeated before approval, restore only the student-owned candidate and generated artifacts from `training-project`:

```powershell
Copy-Item .\boundary-proposal.yaml .\reports\lab01\boundary-proposal.yaml -Force
Remove-Item .\reports\lab01\boundary-decision.json -ErrorAction SilentlyContinue
Remove-Item .\student\design\learning-system-boundary.yaml -ErrorAction SilentlyContinue
```

Do not use these commands after submission without first preserving the submitted commit. To withdraw from the course environment completely, delete the local clone and external training vault only after preserving required work, remove the GitHub fork through its repository settings, and run `gh auth logout` on a shared workstation. Remove installed packages or agent account state only through their official uninstall or account-session controls; do not delete package directories or authentication files manually.

## Final verification

Run the complete deterministic verification from `training-project`:

```powershell
uv run python -m unittest discover -s tests/public -v
uv run learning-project doctor --output .\reports\lab01\environment-report.json
uv run learning-project validate .\reports\lab01\boundary-proposal.yaml
uv run learning-project apply .\reports\lab01\boundary-proposal.yaml --decision .\reports\lab01\boundary-decision.json --output .\student\design\learning-system-boundary.yaml
Get-Content .\reports\lab01\environment-report.json -Raw | ConvertFrom-Json | Out-Null
git remote -v
git branch --show-current
git diff --check
git status --short
```

The self-study sequence is ready for the scheduled demonstration only when all of the following conditions are observable. Instructor grading and acceptance of any manual-fallback justification occur during that demonstration; they are not state-changing laboratory steps that the student must perform in advance:

- all public tests pass;
- the proposal validates;
- an apply without a decision was previously shown to fail;
- the final decision explicitly approves the same `proposal_id` and SHA-256 content digest as the proposal;
- the accepted contract records the approved outcome and supplied attribution and can be regenerated from the proposal and decision; the report and, on an agent path, proposer-session evidence attribute the authority-bearing commands to the student;
- the agent path includes genuine proposer-session evidence, or `REPORT.md` contains the manual-fallback justification and available sanitized failure evidence for instructor review; the fallback makes no AI-authorship or proposer-session claim and explains that it does not demonstrate live AI/student actor separation;
- the second workstation configuration apply converges without unintended reinstallations, or the Linux second capability check reports unchanged versions;
- `origin` is the student's fork, `upstream` is `sobol-mo/ai-systems-design-course`, and the personal branch is not `main`;
- committed paths are under `student/` and `reports/` only;
- the external Markdown vault contains its neutral `README.md`, remains outside Git, and its current off-device protection or known limitation is stated in `REPORT.md`;
- `sources/module-01-ai-engineering-foundations.md` in that vault records the theory path and the complete clone commit, while the vault contains no structured concept, graph-index, or vector-index output;
- the committed and submitted evidence contains no credentials, tokens, authentication secrets, or unrelated private content.

## Submission artifacts

Submit the following items individually in Microsoft Teams rather than as an archive:

- `reports/lab01/REPORT.md`;
- `reports/lab01/environment-report.json`;
- `reports/lab01/provision.log`;
- `reports/lab01/boundary-proposal.yaml`;
- `reports/lab01/boundary-decision.json`;
- `student/design/learning-system-boundary.yaml`;
- selected files from `reports/lab01/screenshots/`;
- the URL of the student's fork, branch name, and exact commit hash.

The submitted commit is the reviewable implementation state. Microsoft Teams is the official timestamped snapshot. Screenshots and logs supplement the deterministic checks; they do not replace them.

## Control questions

1. Which evidence in this laboratory distinguishes an engineered AI-system workflow from a successful model demonstration?
2. Why is `boundary-proposal.yaml` not an accepted system contract even after it passes structural validation?
3. Which actor has proposal authority, which actor has approval authority, which parts of that distinction are enforced by the project CLI, and which parts remain governance rules demonstrated by evidence?
4. Why must a rejected decision not be edited into an approval?
5. What makes the usefulness condition more informative than a statement that the output “looks good”?
6. How does the non-AI baseline help decide whether the AI component is justified?
7. Which workstation evidence demonstrates convergence rather than only successful installation?
8. Which project artifacts are canonical, which are audit evidence, and which are rebuildable derived state?
9. Why is the external Markdown vault kept outside the Git repository, and which recovery mechanism protects it from workstation loss?
10. Which design trade-off was made in the accepted boundary, and what evidence could cause that decision to be revised?
11. What is the difference between `origin` and `upstream` in this laboratory, and which directories may the student commit?
12. Why may a student use a different agent subscription or the documented manual fallback, and which proposal file and deterministic gates must remain the same?

## Optional extension

Create a second proposal for the same intended learning outcome in which the AI component is removed. Compare the two designs using usefulness, verifiability, complexity, cost, latency, and failure risk. Do not replace the accepted laboratory contract. Preserve the comparison only in `REPORT.md` and state which evidence would justify moving from the non-AI baseline to the AI-assisted design.
