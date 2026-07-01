# Speedrun MCAT — demo / test decks

This folder holds **demo and test decks** for developing and testing Speedrun
(review loop, coverage map, the three scores). It is **not** a shipped product deck.

## `speedrun_mcat_demo.apkg` / `speedrun_mcat_demo.csv`

A small (~80 card) MCAT deck spanning the three score-able sections
(Chemical/Physical, Biological/Biochemical, Psychological/Social) with topic tags
suitable for testing the coverage map and per-section scoring.

### Source & license (important)

The card content is **derived from _The WikiPremed MCAT Course_ by John Wetzel**
(<https://www.wikipremed.com/>). WikiPremed's course text is published under a
**Creative Commons Attribution-NonCommercial-ShareAlike (CC BY-NC-SA)** license.

Per the **ShareAlike** term, this derived deck is **also licensed CC BY-NC-SA**
and is for **non-commercial** testing/demo use only. Each card records its
WikiPremed topic + URL in a dedicated **Source** field (named-source rule).

- Attribution: "John Wetzel, an author at wikipremed.com."
- License: <https://creativecommons.org/licenses/by-nc-sa/4.0/>
- ⚠️ The **NonCommercial** term means this deck's content must not ship in a
  commercial product. For a commercial build, replace it with original or
  CC BY-SA / public-domain content. Speedrun's *code* is AGPL-3.0; this *deck
  content* is CC BY-NC-SA (content and code licenses are separate).

### Source pages

| Topic | MCAT section | WikiPremed page |
|---|---|---|
| Work, Energy & Power | Chem/Phys | `mcat_course_code-010103.html` |
| Modern Physics & Atomic Theory | Chem/Phys | `mcat_course_code-010601.html` |
| Acids & Bases | Chem/Phys | `mcat_course_code-021200.html` |
| Amino Acids & Protein Structure | Bio/Biochem | `mcat_course_code-040101.html` |
| Nucleic Acids | Bio/Biochem | `mcat_course_code-040103.html` |
| Nervous System | Psych/Soc (biological foundations) | `mcat_course_code-040701.html` |

`wikipremed_glossary.txt` is the raw extracted term/definition source material.

## Rebuild

```
uv run --no-project --with genanki python decks/build_deck.py
```

## Note on third-party community decks

Popular MCAT decks (AnKing, MileDown, Bouras, MrPankow) are free to download for
**local** study but have **unclear licensing** and must **not** be committed to
this AGPL repository. If you download one for local testing, keep it in this
folder (which is outside any git repo) and do not commit it.
