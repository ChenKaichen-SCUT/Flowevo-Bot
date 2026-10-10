# Flowevo-Bot V4

从00_EXECUTIVE_SUMMARY.md开始，按01–09阅读。机器可读结果均在本目录；逐split的sealed/scored输出及冻结证据在evidence/，原始来源链接在source_extractions.json。

代码：src/flowevo_bot/compositional_v4。使用现有.venv，额外依赖rapidfuzz==3.14.1。运行记录：audit.py → split.py → discover.py → evaluate.py dev-engineering → evaluate.py dev-selection → diagnostics.py → pytest → freeze.py → evaluate.py heldout-confirmation → report.py → verify.py。

split/freeze拒绝覆盖已经冻结的文件；历史结果为只读。重现实验请使用单独工作副本，不重写本目录已发布的原始证据。正式自检命令：`.venv/bin/python experiments/compositional_macro_v4/code/verify.py`。API实验NOT RUN；无需密钥即可重放全部离线结果。
