# Infrastructure

The pipe starts at `TRIM_HORIZON` because stream polling during pipe creation is eventually consistent; using `LATEST` can miss records written during that interval. The projection applies only strictly newer source versions. Poison records are quarantined without advancing projection state, and a separate reconciler measures and optionally repairs missing, extra and mismatched records from the source of truth.

