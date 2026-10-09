# 多轨迹中粒度蒸馏

复用已有627条首轮正确、gold-free 的训练轨迹，未重跑训练。`v2/distiller.py` 同时要求题面结构匹配与成功解答中的多阶段变换证据，保存真实 span、摘录和 trace hash；不是靠单个 reduce/factor 单词聚类。

S07 保留3条：1030（不等式分母符号/排除极点）、902（重复根式代换/范围/回代）、704（齐次比值代换/通分）。S04 选6条具有分类/补集/计数修正链条的题，覆盖重复、顺序与对称。来源选择不读取开发或测试答案。两种 family、结构规则及安全条件是人工设计的先验；具体步骤和短文本由 DeepSeek 从真实轨迹提炼，不能称为从零自动发现算法。

全版本在 data/skills_v2_full.json，簇和证据在 data/clusters.json，来源路径保留。候选由12条旧卡缩为2条修订卡，不把其余10条复制进活跃库。逐条处置见 data/skill_old_new_comparison.csv。

执行了3次付费蒸馏/修订，21,573 tokens。S04 的两次输出曾被本地过严的同义词正则误拒；在开发结果产生前修复 repetition/distinguishability、all orbits equal 的识别，离线采用首次响应，未追加第三次S04调用。两次费用均保留。S07一次成功。此经历也说明字符串 guard 校验只是一道卫生检查，不能替代数学审阅。

短文本上限340 UTF-8 bytes、估计器上限120 tokens（目标约100）；实际两卡估计 105 / 113，这是 bytes/3 估计，非提供商 tokenizer 的精确长度。实际全请求输入 usage 另行记录。

两卡不同学科、不同变换链，来源无重叠。重复程度的文本相似度及来源数量见 evidence/skill_representation_statistics.json。
