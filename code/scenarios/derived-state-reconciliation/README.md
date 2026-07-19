# Source-to-Derived-State Reconciliation

This scenario demonstrates that event delivery and anti-entropy reconciliation are complementary controls.

The planned AWS implementation uses a DynamoDB source table and stream, EventBridge Pipes, a version-aware projection consumer, poison-event isolation and a bounded reconciler. The evidence reports missing, extra and version-mismatched records directly; it does not subtract hashes or call the result entropy.

The source of truth is never modified by projection repair.

