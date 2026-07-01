-- Copyright: Ankitects Pty Ltd and contributors
-- License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
--
-- Speedrun: one row per card joined to its note's tags, for the topic-mastery
-- aggregation. Retrievability is computed by the engine's registered
-- extract_fsrs_retrievability() scalar function and is NULL for cards without
-- FSRS memory state (e.g. new/unreviewed cards). Bound parameters, in order:
--   ?1 = timing.days_elapsed
--   ?2 = timing.next_day_at
--   ?3 = timing.now
SELECT c.id,
  n.tags,
  c.type,
  extract_fsrs_retrievability(
    c.data,
    CASE
      WHEN c.odue != 0 THEN c.odue
      ELSE c.due
    END,
    c.ivl,
    ?,
    ?,
    ?
  )
FROM cards c
JOIN notes n ON c.nid = n.id
