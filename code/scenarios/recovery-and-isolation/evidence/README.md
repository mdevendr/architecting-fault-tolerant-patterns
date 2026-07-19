# Evidence

Local simulator outputs and AWS cloud evidence must remain visibly separate.

Cloud evidence is accepted only when it includes:

- a run ID and Git commit;
- deployed resource identifiers and Region;
- baseline and protected configurations;
- fault start, recovery start, and completion timestamps;
- raw or exported CloudWatch metrics;
- automated contract results; and
- documented limitations.

Generated run data is ignored by Git by default. Sanitized, reviewed evidence can be added deliberately under a tagged release.

