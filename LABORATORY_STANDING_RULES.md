# Laboratory standing rules

These rules apply to every laboratory in this course. Each laboratory file adds only the artifacts, screenshot filenames, and report sections that are specific to that exercise. The due date of a laboratory is the due date of the corresponding Microsoft Teams assignment.

The student reads these rules together with the laboratory being performed. Microsoft Teams does not add further academic rules.

## Report content

The report records the work that was performed, not only the final results. It describes the course of execution in enough detail that another reader can follow what was done, in which order, and why.

The report includes the required screenshots named in that laboratory. Each screenshot must uniquely identify the author and the date of capture: the operating-system account or GitHub login and the system date must be visible in the image (`Get-Date` or `date` in the same terminal, or the visible clock). A caption in the report does not replace that visible identification.

The report contains a dedicated identity section with the URL of the student's GitHub fork, the personal branch name, and the complete commit hash of the submitted work.

A one-page report cannot receive a high mark.

The submitted narrative report is written in Ukrainian.

## Submission

Reports are uploaded to the corresponding Microsoft Teams assignment. The narrative report is one Markdown file named `REPORT.md`. That file is attached directly; a link is not a submission.

The laboratory may also require a small set of machine-readable evidence files. Those files are attached individually. An archive is not accepted.

The source report in Git uses relative Markdown image paths into `reports/labNN/screenshots/`. The Teams narrative file is the copy produced by `learning-project prepare-report`, which embeds those images so Teams can render one Markdown attachment. The student runs that command as written in the laboratory. The generated file `reports/labNN/submission/REPORT.md` may be committed to the fork.

## Academic integrity

Reports that show plagiarism, copying, or identity with another student's work are not accepted for credit.

Using the course-documented agent path to draft a laboratory proposal is not plagiarism. Copying another student's report, screenshots, or machine-readable artifacts is.

## Recording of results

After successful defence of all laboratories at the end of the semester, grades are transferred into the academic group's grade record.

## Deadlines

Each laboratory has a deadline: the due date of its Microsoft Teams assignment. Missing that deadline reduces the grade by one point. Work submitted after the credit week may be reviewed in the following semester.

Work is accepted one laboratory at a time.
