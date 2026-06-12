# Checkpoints

## Stable Commits

- `696b4fc chore: add automation baseline and workspace cleanup`
  - Consolidated non-core workspace material.
  - Added goal, changelog, and review checklist.
  - Added initial evaluation dataset and backend integration fixes.

- `93a90fd feat: add safety layer ablation controls`
  - Added request-level safety-layer ablation switches.
  - Extended the evaluation runner with named ablation suites.

## Rollback Notes

Use non-destructive inspection before rollback:

```powershell
git status --short
git log --oneline -5
git diff
```

Only run destructive rollback commands after explicit user approval.

## Next Checkpoint Candidate

Commit the expanded evaluation corpus, Markdown report helper, reproducibility fixes, and latest expanded ablation snapshot.
