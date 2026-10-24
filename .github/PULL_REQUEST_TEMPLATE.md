## What changed

<!-- One or two sentences. State the result, not the intent. -->

## Why

<!-- What was wrong, or what this makes possible. If a figure in README.md or
CHANGELOG.md moved, say which one and to what value. -->

## Verification

<!-- Paste the summary from tools/runtests. A PR that leaves a certificate
failing is not mergeable. -->

```
$ tools/runtests
TOTAL       ...      ...        0
ALL CERTIFICATES PASS
```

- [ ] `tools/runtests` passes (all nine certificates)
- [ ] `python3 tools/check_repo.py` passes
- [ ] new behaviour has a certificate, and the certificate asserts something
      independent of the implementation
- [ ] documentation still matches what the code does

## Scope

- [ ] affects only `oncopattern/**` (this repository)
- [ ] touches the TECH toolchain — linked upstream issue: #
- [ ] adds or changes a fixture under `datasets/` (say how it was generated)
