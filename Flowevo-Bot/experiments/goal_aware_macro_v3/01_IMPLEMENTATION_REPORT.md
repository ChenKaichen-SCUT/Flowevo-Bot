# Goal-Aware Executable Skills V3 实现

本地与远端起点均为245ce20d9cc7a70ac8f5119bf29d374039d24a53，仅指引.txt变化。独立目录goal_aware_macro_v3；历史3569个文件SHA被保护，上游、V1、V2和RMMD均不改写。

新增src/flowevo_bot/goal_v3：goals.py定义结构化Goal与闭合题意文法；engine.py实现Goal→Preconditions→Execute→Verify→Commit；learning.py执行受限程序合成；runtime.py实现三组对照及完全相同的无库回退。部分中间量不执行、不注入prompt。所有当前题gold仅进入提交后的独立评分，未进入Goal Parser、Solver、Bank或恢复逻辑。

支持目标：全部根和、根积、两两乘积和、2–6次幂和、合法倒数和、有界对称有理表达式、多项式余式。支持数值多项式/非零右端方程归一化、显式根绑定、完整实根数量与开放区间约束、分数及指定小数格式。目标必须由整个文法消费，未知附加句不能丢弃。仅出现roots/remainder不允许完整执行。

根多项式QQ、次数2–6、首项非零；无显式重数说明的直接请求要求squarefree；显式counting multiplicity或与次数相同的完整命名根绑定允许重根。正根/实根/有理根的子集、变量参数、不明确根数量、未解析条件均拒绝。倒数检查常数项，保留原始分母并用根置换轨道的非零值验证定义域；不能只在约分后检查分母。幂次、表达式大小和分母类型均有上界。

人工计算采用Vieta/Newton、对称多项式化及精确余式。核验分别采用伴随矩阵的迹/行列式/逆矩阵、独立Groebner残差、系数递推与P=QD+R恒等式及次数界。数学证书与语义文法证书分开记录；格式化失败也不能Commit。

Goal与ReasoningOperation有类型定义；自动bank用限定JSON AST执行并由MacroSkill的Pydantic模式复核（data/macro_skill.schema.json）。该类型化归档校验在分析阶段加入，不改变冻结求解器。禁止exec/eval任意模型程序。DSL只有固定系数/奇偶特征、负号和四则运算，最多5节点。

付费与本地并发上限64/12，预算120调用/200000 tokens，DeepSeek Flash、温度0、max_tokens4096。实际付费门槛失败，没有读取密钥执行模型实验。新增调用0。原始独立池运行代码及22个文件hash固定于pre_reserved_freeze.json和runtime_before_reserved.zip，之后没有改动这些文件。
