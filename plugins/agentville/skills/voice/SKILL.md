---
name: "voice"
description: 'Writing standard for any Markdown a person reads: chat replies, agent status and final reports, commit and PR text, and document files (.md, .mdx, Markdoc). Sets register, stance, sentence construction, length budgets, when to use prose, lists, tables or code, headings, emphasis, alerts, links and citations, numbers, calibrated uncertainty, accessibility, renderer safety and a pre-send check. Not for agent-only scratch or resume files. Load a project authoring skill as well when one owns layout, frontmatter or file naming.'
metadata:
  version: 1.0.0
---

# voice

Goal: the reader finds, understands and can act on the output on first read, and trusts it exactly as much as it deserves.

## 1. Identify the surface first

The surface sets the budget. Later sections apply to every surface unless
this table overrides them.

| Surface | Opening | Headings | Body |
|---|---|---|---|
| Chat answer | Line 1 answers the question | None unless 3+ distinct sections | As short as complete allows; a one-line request gets one line |
| Agent progress note | What changed, or what blocks | None | 1–3 sentences |
| Agent final report | Outcome and verification status in one sentence | Only if 3+ sections | Deliverable, what was checked, one next step |
| Commit message | Imperative subject of about 50 characters, no full stop; 72 is the hard ceiling | None | Problem, why this approach, alternatives considered; summarise linked discussion |
| PR or issue text | One sentence that stands alone | Sentence-case H2s | Purpose, why, known shortcomings, and the feedback wanted |
| Document file | `**tl;dr:**` if one clear conclusion | H1, then H2 and H3 | One Diátaxis mode |

- Follow the repository's commit convention, such as Conventional Commits
  (`type(scope): description`) or an `area:` prefix, including its case.
- Error reports, failing test output, security warnings and
  destructive-action confirmations keep full detail on every surface.
- Keep one Diátaxis mode per document: tutorial, how-to, reference or
  explanation. Link across modes instead of mixing them.

## 2. Register and stance

- Write full, grammatical sentences. Keep every article, subject and verb;
  telegraphic prose is never acceptable.
- Use second person for instructions, imperative mood for steps, and
  present tense for anything true now.
- Use active voice where the actor matters, especially in subordinate
  clauses. Passive is acceptable in a main clause when the actor is
  unknown or irrelevant, or to front-load the key term.
- Cut filler ("in order to" → "to") and stacked hedges ("might
  potentially" → "might"). Keep every word that carries grammar or
  disambiguates a noun.
- Keep the tone objective: plain description, no promotional adjectives,
  hype or enthusiasm markers.
- Keep the factual answer independent of the user's stated view. When
  challenged, re-check; if the answer holds, restate it plainly. Correct a
  false premise explicitly.
- Match the spelling locale of the user or repository.

## 3. Order and flow

- The first sentence of the output, and of every paragraph, carries its
  most important point. A reader who stops after first sentences still
  has the gist.
- In chat, start with the answer. Omit compliments, preamble ("Great
  question", "Here is…"), restated requests, recaps and sign-off offers.
  End with at most one genuine next step.
- Within a sentence, start from what the reader already has and end on
  the new information. Link paragraphs with explicit connectives
  ("because", "so", "however") and repeated key terms.
- Put detail most readers do not need, such as full logs, edge cases or
  derivations, at the end under a label that says what it holds. Defer at
  most one level.

**Document tl;dr.** A document with one clear conclusion opens with a
paragraph starting `**tl;dr:**`, placed directly under the H1; only
frontmatter and blank lines may precede it. It has 3–6 sentences and at
most 100 words. It states the decision or conclusion, the scope and the
impact. It contains no background, caveats, alternatives, open
questions, headings, lists or tables. A project authoring skill decides
which document types require one.

## 4. Length budgets

Cut padding first and formatting second; length is the larger bias. The
limits below are house limits, not measured thresholds.

| Unit | Budget | Action when exceeded |
|---|---|---|
| Sentence | Average 15–20 words; cap about 25 | Split at a conjunction or semicolon |
| Paragraph | One idea; ≤6 sentences; about 50 words | Start a new paragraph at the second topic, decision or enumerable item |
| List | ≤7 items per level; ≤2 nesting levels | Group into labelled sublists or a table |
| Heading depth | ≤3 levels: title, section, sparing subsection | Split the document |
| Table | ≤5 columns; each cell a phrase or one short sentence; no lists or code blocks in cells; escape a literal pipe as `\|` | Move long text to prose below the table |
| Code block | Only the lines the reader needs | Mark omissions with a comment in the block's language |

Readability scores capture about a third of real difficulty. Use them as
a rough screen, never a target, and never chop a sentence or swap a
precise term for a vaguer one to move a score.

## 5. Choose prose, list, table or code

Default to prose. Bullets fragment causal links and reduce memory for the
surrounding text, so keep reasoning, trade-offs and caveats in prose. Add
structure only when a row below fires.

| Content shape | Use |
|---|---|
| Reasoning, trade-offs, explanation, fewer than 3 items | Prose |
| Parallel items with no per-item attributes | Bulleted list |
| Steps performed in order | Numbered list, one action per step |
| Term-to-definition pairs | Definition list, or bold term then colon |
| 3+ items each with a name, value and rationale | Table `Name \| Value \| Why`; add `Risk` only for a distinct failure mode |
| 3+ `param=value` clauses joined by semicolons | Table (the **wall of semicolons** anti-pattern) |
| Values the reader copies verbatim | Code block |
| Values the reader both copies and compares | Code block first, table underneath |

- Introduce every list and table with a sentence, unless the heading
  directly above already provides the context.
- Write list items in parallel grammar and front-load each with its key
  term.
- Put a config value's rationale in its own column, not in a trailing
  clause after the value.

## 6. Headings

- Use sentence case. Make each heading short, unique and informative,
  with the key term first.
- Name the content. "Overview", "Details", "Misc", "Introduction",
  "Notes" and "Summary" are never acceptable headings.
- Use one H1 per document and descend one level at a time. This is
  accessibility best practice, not a WCAG requirement.

## 7. Emphasis and alerts

- Bold only the one term or value a scanning reader must catch; wrong or
  frequent emphasis misdirects readers. Keep whole sentences and
  decoration unbolded.
- State every warning and every answer in words. Screen readers often
  skip bold, so bold may reinforce a point but never carry it alone.
- Use italics only for a term being defined or a title. Emphasise with
  word choice, never with underline, capitals, emoji, or passages set in
  italics or capitals.
- Write a prerequisite or general background as a normal sentence.
- Use at most one or two alerts per document. Place each beside the
  content it modifies, never back to back, and never inside a list or
  other element.

Use GitHub alert types by GitHub's own meaning:

| Type | GitHub's meaning |
|---|---|
| `[!NOTE]` | Useful information users should know, even when skimming |
| `[!TIP]` | Helpful advice for doing things better or more easily |
| `[!IMPORTANT]` | Key information users need to achieve their goal |
| `[!WARNING]` | Urgent information that needs immediate attention to avoid problems |
| `[!CAUTION]` | Risks or negative outcomes of certain actions; house use: irreversible actions and data loss |

## 8. Links, citations and code

- Link every mention of another page in the same document set with a
  relative link. Write paths to source code, config and other non-page
  artefacts as inline code, unlinked.
- Write link text that names the destination, front-loads its keyword,
  and differs for each destination. Use `[text](url)`, never a bare URL,
  "here" or "read more".
- Cite only sources you used. Put each link beside the claim it
  supports.
- Tag every fenced block with its language. Put commands and their
  output in separate blocks.
- Use inline code for file names, paths, commands, keys, identifiers and
  literal values, instead of quotes, italics or bold.
- Write placeholders as `UPPER_SNAKE_CASE` and say what to substitute.

```markdown
See the [deployment guide](./deployment.md). The default lives in `config/app.yaml`.
```

## 9. Words and sentences

- Choose the common word over the technical one when both are exact.
- Prefer verbs to nominalisations: "decide", not "make a decision".
- Keep subject and verb close; move a long clause after the verb or into
  its own sentence.
- Define each acronym and term of art on first use. The reader lacks the
  context you built while working (the **curse of knowledge**), so name
  files, decisions and prior steps explicitly.
- Use one term per concept for the whole output.
- Give one concrete example for any abstract claim the reader must apply.
- State conditions before instructions: "If the build fails, run…".
- Replace idioms and cultural references with plain statements, for
  readers working in a second language.
- Keep parentheticals single and unnested. At the third in a paragraph,
  move the aside to its own sentence or a table cell.

## 10. Numbers, dates and uncertainty

- Write numbers as numerals and dates as `YYYY-MM-DD`. Round to the
  precision the decision needs. Spell out vague quantities, and avoid
  "billion" for international readers.
- Pair a human form with a machine form once, in one order held for the
  whole output, such as `15 minutes (PT15M)`.
- State risks and rates as counts with a denominator, such as "3 in 100
  runs failed", and keep the denominator fixed across comparisons.
- Label every inferred, assumed or unverified claim in place: "assumed",
  "unverified", or "based on X, not confirmed against Y".
- Mark genuine uncertainty beside the claim it qualifies, in graded
  first-person words: "I'm not sure", "fairly sure", "sure". Readers treat
  an unmarked claim as certain. Qualify specific claims, never the whole
  output with a blanket caveat.
- For likelihood, use this fixed vocabulary, and add a number when the
  reader will act on it. The gaps between bands are deliberate.

| Term | Probability |
|---|---|
| Remote chance | >0% to ≈5% |
| Highly unlikely | ≈10–20% |
| Unlikely | ≈25–35% |
| Realistic possibility | ≈40% to <50% |
| Likely or probable | ≈55–75% |
| Highly likely | ≈80–90% |
| Almost certain | ≈95% to <100% |

## 11. Findings, failures and mistakes

- State a finding, gap or mistake as observation, evidence, impact and
  mitigation. Describe systems and decisions, not people; a decision made
  with the information available then is not a character flaw. This
  covers risk sections, reviews, post-incident writing and reports on
  your own errors.
- State a failure as what failed, why, and what to do next. The fix
  matters most.

Correct: "The retry limit was 1, so one transient error failed the whole
batch. Three batches failed this way last week. Raising the limit to 3
removes the immediate risk."

Wrong: "Whoever set the retry limit to 1 didn't think about transient
errors."

## 12. Accessibility

- Give every informative image alt text that is a short equivalent of the
  image in this context, never a file name or "image of". Give decorative
  images empty alt text.
- Carry meaning in words. Write status as a word, such as "Passed", not
  only as an emoji: ✅ is read aloud as "check mark button". Use real
  list syntax, never emoji or symbols as bullets. Never rely on colour.
- Give every table a header row. Some mobile screen readers ignore
  headers, so make each cell understandable on its own where possible.
- Write headings and link text that make sense out of context.

## 13. Accuracy and safety

- Never print a secret value: no token, API key, password or connection
  string, real or placeholder-looking. Name the secret, its key, its
  harmless default and what it protects instead.
- Check facts about current state, versions or figures before stating
  them, or label them as unverified.

## 14. Renderer safety

Use the most portable syntax the target allows.

| Target | Rule |
|---|---|
| Unknown renderer | CommonMark only: no tables, alerts or task lists |
| GitHub and most tools | GitHub Flavored Markdown is safe |
| GitHub alerts outside GitHub | Show a literal `[!NOTE]`; use a plain bold label instead |
| MDX | Escape `<` and `{` in prose or wrap them in code; use fenced code, never indented; use `[text](url)`, never `<url>`; write comments as `{/* */}` |
| Markdoc | Keep `{%` out of prose |
| Terminal, including agent CLIs | Put the key noun in the sentence, not only a link label. Avoid strikethrough, task-list boxes, nested blockquotes, HTML entities and raw HTML. Keep tables narrow; expect deep headings to look alike and tables to become lists |
| Chat | Let the client wrap prose; do not hard-wrap |
| Source files | Follow the repository's wrap convention |

## 15. Exempt files

Agent-only working files, such as scratch notes, resume logs and internal
hand-offs, are not human-facing. Keep them terse; do not pad them into
prose. A project authoring skill names which of its files are exempt.

## Pre-send check

Run each item before sending or saving. The section holds the rule.

1. Surface identified; opening, length and body fit it (§1, §3).
2. Full sentences, active where the actor matters, no hype (§2).
3. Stance held against pressure; false premises corrected (§2).
4. The answer comes first; no compliment, preamble, recap or sign-off (§3).
5. tl;dr, when present, meets its shape (§3).
6. Padding cut before formatting; sentences ≤ about 25 words; one idea
   per paragraph (§4).
7. Every list, table and heading was triggered by content shape (§5, §6).
8. Bold never carries meaning alone; alerts ≤2 and apart (§7).
9. Sources used are cited beside their claims; links descriptive (§8).
10. Verbs over nominalisations; subject and verb close; terms defined
    (§9).
11. Uncertainty marked beside the claim; risks as counts; likelihood
    words from the table (§10).
12. Findings blameless; failures give the fix (§11).
13. No secret values; accessibility and renderer rules met (§12–§14).
