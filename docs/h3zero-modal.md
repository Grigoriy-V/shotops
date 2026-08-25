# H3Zero on Modal

This is the reproducible source and deployment note for the experimental
`--provider h3zero` route. The provider integration itself is documented in
[usage.md](usage.md).

## Pinned source

- Upstream: `https://github.com/hui-tony-zk/h3zero`
- Tested commit: `8655e33d2b5a6f670458aa783a6d44b1c659d7e8`
- Local checkout: `.tools/h3zero/` (gitignored)
- Local Python: 3.11 virtual environment at `.tools/h3zero/.venv/`

The upstream no-GPU suite passed at that commit: 57 Python tests, 35 frontend
tests, and 4 Node/orchestration tests. The production npm dependency graph had
no reported vulnerabilities; the full development graph reported one high
severity advisory.

Clone and verify the exact revision before doing anything that can allocate
cloud resources:

```powershell
git clone https://github.com/hui-tony-zk/h3zero .tools/h3zero
git -C .tools/h3zero checkout --detach 8655e33d2b5a6f670458aa783a6d44b1c659d7e8
git -C .tools/h3zero apply ..\..\tools\h3zero-proxy-auth.patch
```

The patch changes only the ASGI decorator and requires Modal proxy
authentication. Do not deploy the upstream public default: its job endpoint can
allocate an RTX PRO 6000 for anyone who discovers the URL.

For an interactive local client, `modal curl` obtains short-lived endpoint
authorization from the existing Modal profile. It does not copy the Modal
account token into this repository. For unattended clients, create a dedicated
Modal proxy token and keep it in the gitignored `.env`.

## Cost and licence gates

Do not run H3Zero's `setup`, model download, GPU deploy, smoke test, or an API
job without an explicit approval for that run. The initial model volume is
about 98 GiB. A first `turbo_4` job is 480p; cold start and model loading can
cost more than the generation itself.

MiniMax H3's licence defines an Applicable Territory that excludes the United
States, European Union, United Kingdom, and Republic of Korea. Modal normally
uses US infrastructure for some storage traffic even when compute is routed to
another region. Region selection alone therefore does not establish licence
compliance. Resolve that deployment question before weights are downloaded to
Modal.

## First evidence

The first paid result is not acceptance evidence by itself. Run generation with
`--extract`, then compare it against the same take at matched normalised times:

```powershell
$env:PYTHONPATH="src"
python -m ai_render generate projects/nyc/sequences/seq_010/sh_0010/street_a.json `
  --provider h3zero --extract
```

Record whether H3 holds camera motion, framing, object positions, and duration.
Reference ingestion proves only that the API accepted the files; it does not
prove structural adherence.
