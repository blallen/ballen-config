# RTK

agent-run shell commands must be prefixed with `rtk`.

## Supported command patterns

```bash
rtk git status
rtk cargo test
rtk npm run build
rtk pytest -q
```

## Meta commands

```bash
rtk gain
rtk gain --history
rtk proxy <cmd>
```

## Verification

```bash
rtk --version
rtk gain
which rtk
```
