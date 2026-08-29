# Working rules for cloud sessions in this repo

Canonical source is the Notion page **🔌 Cloud Session Capability Ledger**
(under *Claude Code Memory*). Notion stays human-editable and authoritative;
this file exists so a cloud session picks the rules up automatically, with no
prompting. If the two disagree, Notion wins — and say so rather than
silently following this copy.

## Standing rules

1. **A mock passing does not license a real call.** A mock encodes the
   session's assumptions about the API. It is scaffolding, never evidence.
   Receipts, probe outputs, and CI artifacts must never come from a mock.
2. **The mock's only job** is to make the day-you-get-tokens work be "change
   the base URL and run the probe", not "start building".
3. **The container is scratch space, never storage.** It is reclaimed after
   inactivity. Only pushed git state survives. Anything worth keeping gets
   committed or handed to the user before the session goes idle.
4. **Never hand personal credentials to a session.** Sandbox or throwaway
   tokens in env vars only.
5. **Env vars are not a secret store.** Anyone with environment access can
   read them. Mint scoped throwaway keys per event; revoke after submission.
6. **Env vars are copied once, at session start.** A running session never
   sees a value added afterwards. Add it, then open a *new* session.

## The boundary

Not "strategy vs. execution" — it is **text vs. network**. Anything
terminating in words works. Anything terminating in an outbound call to a
non-allowlisted host is blocked until the allowlist is edited.

**But check which environment you are in before believing that.** Egress
policy is per-environment, and this one is unrestricted (the agent proxy
reports `selective: false`, meaning no host allowlist). In such an
environment WebFetch, yt-dlp and arbitrary APIs all work. The ledger's rule
"WebSearch works, WebFetch does not" is true of a *default-allowlist*
environment, not of every environment. Verify with:

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"     # selective: true|false
```

## Do not conclude something is impossible without checking

The ledger contains at least one correction to a conclusion a previous
session got wrong. Before reporting a hard limit, check it. If you hit a
blocker that is genuinely not listed, say so explicitly and name the section
it belongs in — the user appends it. Do not edit Notion unasked.

## Two failure modes specific to this work

**A blocked fetch is not a blocked task.** When a host blocks *this
container* (IP reputation, not policy), the fix is usually to have a
third-party server fetch it instead of fetching it here. Worked example:
YouTube returns 429/`IpBlocked` to datacenter IPs, but Gemini ingests a
YouTube URL natively because Google's servers do the fetching.

**Metadata succeeding is not content succeeding.** The same blocked host will
often serve titles, durations and playlist listings perfectly while refusing
the actual payload. A pipeline that only checks "did I get a response" will
report success on an empty corpus.
