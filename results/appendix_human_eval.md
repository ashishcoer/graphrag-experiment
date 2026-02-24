# Appendix: Human Evaluation Protocol

## A.1 Likert-Scale Evaluation Rubric

Evaluators scored each system output on three dimensions using a 5-point Likert scale.

---

### Dimension 1: Relevance
*Does the output directly address the work-intake query?*

| Score | Label | Description |
|---|---|---|
| 5 | Excellent | Fully and precisely addresses all aspects of the query; no off-topic content |
| 4 | Good | Mostly addresses the query with only minor gaps or tangential content |
| 3 | Adequate | Addresses the main topic but misses important aspects or includes notable irrelevancies |
| 2 | Poor | Only superficially related to the query; significant content is off-topic |
| 1 | Irrelevant | Does not address the query; completely off-topic or generic |

---

### Dimension 2: Completeness
*Does the output cover the required work-intake planning sections?*

The five required sections are: **Taxonomy**, **Routing/Ownership**, **Dependencies**, **Clarifying Questions**, and **Acceptance Criteria**.

| Score | Label | Description |
|---|---|---|
| 5 | Excellent | All 5 sections present and substantively addressed |
| 4 | Good | 4 of 5 sections present, or all 5 present but one is superficial |
| 3 | Adequate | 3 of 5 sections present with reasonable depth |
| 2 | Poor | Only 1–2 sections present or all sections are superficial |
| 1 | Incomplete | No recognisable structure; missing most or all required sections |

---

### Dimension 3: Coherence
*Is the output well-structured, clear, and professionally written?*

| Score | Label | Description |
|---|---|---|
| 5 | Excellent | Exceptionally clear, logically organised, professional language throughout |
| 4 | Good | Clear and well-organised with only minor stylistic issues |
| 3 | Adequate | Generally understandable but with some unclear passages or inconsistent structure |
| 2 | Poor | Difficult to follow; significant structural or language problems |
| 1 | Incoherent | Cannot be understood; severely disorganised or grammatically broken |

---

### Overall Preference
After scoring all four systems, evaluators indicated their **overall preferred system** (System-A, B, C, or D) — the output they would find most useful as a work-intake planning document in a real software engineering context.

---

## A.2 Full Annotator Instructions

```
HUMAN EVALUATION INSTRUCTIONS
==============================

OVERVIEW
--------
You will evaluate outputs from 4 AI planning systems (labelled System-A to
System-D) on work-intake planning tasks derived from real GitHub issues.
The system labels are anonymised -- you will not know which underlying
system produced which output until after all evaluations are complete.

YOUR TASK
---------
For each of the 75 items in the spreadsheet:

  1. Read the QUERY column carefully (GitHub issue title + description)
  2. Read the outputs from System-A, System-B, System-C, System-D
  3. Score each output independently on THREE dimensions (1-5 scale)
  4. Select the ONE system you would most prefer for real-world use

SCORING DIMENSIONS
------------------

RELEVANCE (1-5)
  Does the output directly address the work-intake query?
  5 = Fully and precisely addresses all aspects of the query
  4 = Mostly relevant with only minor gaps
  3 = Addresses main topic but misses important aspects
  2 = Only superficially related; significant off-topic content
  1 = Does not address the query at all

COMPLETENESS (1-5)
  Does the output cover the 5 required sections:
  Taxonomy, Routing/Ownership, Dependencies,
  Clarifying Questions, and Acceptance Criteria?
  5 = All 5 sections present and substantive
  4 = 4 of 5 sections present
  3 = 3 of 5 sections present
  2 = Only 1-2 sections present
  1 = No recognisable structure

COHERENCE (1-5)
  Is the output clear, well-structured, and professionally written?
  5 = Exceptionally clear and logically organised
  4 = Clear with only minor stylistic issues
  3 = Understandable but some unclear passages
  2 = Difficult to follow
  1 = Cannot be understood

PREFERRED SYSTEM
  After scoring all four, enter A, B, C, or D for the system
  you would most prefer as a real work-intake planning document.

IMPORTANT GUIDELINES
--------------------
- Score each system INDEPENDENTLY -- do not let one score influence another
- Ignore formatting differences (markdown, bullet points, headers) --
  focus on the CONTENT, not the presentation style
- If two systems score equally on a dimension, giving the same score is fine
- If an output appears to be an error message, score it 1 on all dimensions
- Use the NOTES column for any observations
- You may take breaks -- your progress is saved in the spreadsheet
- Complete ALL 75 rows before returning the file

TIME ESTIMATE
-------------
Most evaluators complete this in 2-3 hours.
We recommend doing it in two sessions of ~90 minutes each.

QUESTIONS?
----------
Contact the research team before starting if anything is unclear.
Do NOT discuss your ratings with other evaluators until after submission.
```

---

## A.3 Sample Evaluated Output (Illustrative Example)

The following example illustrates how a single item was presented and scored.
This instance is drawn from the evaluation set (ID: bench_0010).

---

**Query (presented to evaluators):**

> *WARNING - Connection schemes (type: google_cloud_platform) shall not contain '_' according to RFC3986. Apache Airflow raises a warning that the connection scheme for google_cloud_platform contains an underscore, which violates RFC3986 URI standards. The get_uri method needs to be updated to handle this case.*

---

**System-A output (excerpt, first 400 characters):**

> *Based on the provided request and evidence, here is the revised structured output:*
> *### 1. TAXONOMY CLASSIFICATION*
> *The issue pertains to the connection schemes in Apache Airflow, specifically the `get_uri` method for connection types. The problem is that the connection scheme for `google_cloud_platform` contains an underscore, which violates RFC3986 standards.*
> *### 2. ROUTING/OWNERSHIP*
> *This issue should be routed to the Apache Airflow development team...*

**System-B output (excerpt):**

> *### Taxonomy*
> *1. **Connection Schemes** - Definition: The format or structure of a connection string used to connect to a service. Examples: `google_cloud_platform`, `postgresql`, `mysql`.*
> *2. **RFC3986** - Definition: A standard that defines the syntax of Uniform Resource Identifiers (URI). Key Points: URIs must not contain certain characters, such as underscores.*

**System-C output (excerpt):**

> *### 1) Taxonomy*
> *#### Categories:*
> *- **Connection Schemes**: Methods and protocols used to establish connections.*
> *- **RFC3986 Compliance**: Standards for Uniform Resource Identifiers (URI).*
> *- **Apache Airflow**: Workflow automation and scheduling system.*

**System-D output (excerpt):**

> *### Taxonomy*
> *1. **Apache Airflow Version**: 2.7.1, 2.10.1, 2.9.1, 2.9.3*
> *2. **Issues**: Connection schemes containing underscores, Jinja templating misinterpretation...*

---

**Illustrative annotator ratings for this item:**

| Annotator | Rel-A | Rel-B | Rel-C | Rel-D | Comp-A | Comp-B | Comp-C | Comp-D | Coh-A | Coh-B | Coh-C | Coh-D | Preferred |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Evaluator 1 | 5 | 4 | 4 | 4 | 5 | 3 | 3 | 3 | 5 | 4 | 4 | 4 | A |
| Evaluator 2 | 5 | 4 | 5 | 4 | 5 | 3 | 4 | 3 | 5 | 4 | 5 | 4 | A |
| Evaluator 3 | 5 | 4 | 4 | 3 | 5 | 3 | 3 | 2 | 5 | 4 | 4 | 3 | A |

*Note: System labels (A/B/C/D) are randomised per instance. The mapping to actual pipeline names is revealed only after all evaluations are complete (see unblinding key).*

---

## A.4 Evaluation Summary Statistics

| Metric | Value |
|---|---|
| Total evaluators | 10 |
| Instances per evaluator | 75 |
| Total preference judgements | 750 |
| Task types | Taxonomy (25), Routing (25), Dependency (25) |
| Repositories covered | 4 (Kubernetes, VS Code, Home Assistant, Airflow) |
| Random seed for sampling | 42 |
| Pipeline order randomised | Yes (per instance) |
| Annotator blinding | Yes (pipeline names hidden until after evaluation) |
| Inter-annotator agreement metric | Fleiss' kappa (κ) |