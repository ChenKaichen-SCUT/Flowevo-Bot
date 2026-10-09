# Sources and licenses

New integration code: Flowevo-Bot research prototype, 2026. Files in `src/code_math/baseline.py` adapt the mathematical prompt and historical-context behavior of FlowEvo and explicitly carry a modification notice. Other new components reimplement the architecture described in the user's 指引.txt.

- FlowEvo, DEFENSE-SEU, https://github.com/DEFENSE-SEU/FlowEvo, commit `36e81efd4d1fdbabca7366200b15808ebef157fa`; Apache-2.0 text retained verbatim in `licenses/FlowEvo-LICENSE` and `vendor/flowevo/LICENSE`. `vendor/flowevo/src/` is the local source snapshot, including the user's earlier local modifications. It is not silently represented as an unmodified upstream release.
- Buffer of Thoughts, Ling Yang et al., https://github.com/YangLing0818/buffer-of-thought-llm, commit `b46ac813cc2aa2c8f98aa93022d0e491b3862cfc`; MIT, Copyright (c) 2024 Ling Yang. License retained verbatim in `licenses/BoT-LICENSE` and `vendor/bot/LICENSE`. The relevant local pipeline/template files are preserved for audit. The new distiller follows the thought-template abstraction idea but batches multiple clean traces and does not invoke the original RAG pipeline.
- MATH local data originate from EleutherAI/hendrycks_math revision `21a5633873b6a120296cce3e2df9d5550074f4a3`, originally downloaded in this workspace. Its data card is retained in `licenses/MATH-DATASET-CARD.md`.

No `.git`, virtual environment, cache, API key, secret override, or historical run output was copied into vendor. Source snapshots are provided for reproducible comparison, not automatic execution. Their legacy gold-assisted mathematical retry is NOT part of the new default evaluation pipeline.
