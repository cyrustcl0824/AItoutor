# ChinaTextbookStudyFree Web adaptation

This Next.js web application replaces the earlier Vite client and adapts the
mobile-first English learning flow and visual language from ChinaTextbookStudyFree
commit `7824f0b4cd2ff8cac24ecca80864019b37ed7ba6`.

Source: https://github.com/cyrustcl0824/ChinaTextbookStudyFree

The complete platform-independent upstream Core is vendored at `packages/core`
with its MIT license. Learning progress in this adaptation is stored only by the
FastAPI service; upstream local game-economy persistence is intentionally omitted.
