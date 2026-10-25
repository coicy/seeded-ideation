# Seeded Ideation v1.7 | 至少64条独立种子路径 + 逐轮减半 + 通用设计工作流

**核心目标：让 Agent 从设计需求到可交付方案形成可复核的闭环，同时保留可追溯的随机种子创意发散能力。**

该技能适用于游戏、软件、界面、服务、文案等，不预设保守创新或颠覆式创新。用户的本次要求决定边界。随机种子只负责为探索提供可追溯的外部扰动。

## 安装

解压 `seeded-ideation` 至 Agent 支持的 skills 目录，例如 `%USERPROFILE%\.codex\skills\seeded-ideation\`。Python 3.9+，无第三方依赖。

## 通用设计流程（v1.5）

`需求界定 → 调研/分析 → 方案探索 → 取舍决策 → 详细设计 → 检查/验证/迭代 → 交付`。支持游戏机制、UI、软件架构、服务、视觉、内容与其他设计任务。按任务选 `quick`（轻量）、`standard`（标准）或 `rigorous`（高要求）；如只需一个方案，选 `direct`，需要备选则选 `compare`。

- **设计输入：** 用户目标、实际设计对象、已知背景、硬限制与许可修改的范围；不可凭空补全未知事实。
- **研究与决策：** 真实证据和假设分开；比较成本、体验、可实现性与风险，不虚构用户批准。
- **可实施输出：** 交付适用于当前领域的设计工件，并将硬需求关联到可观察的验收条件。
- **验证闭环：** `pass/fail/blocked/not_run` 显式记录，失败要修订并复测；没有运行的测试不标为通过。
- **随机性是可选组件：** 只有需要扩大探索空间时才启动 `plan/batch/funnel`；一旦启动，至少64个独立种子，并逐轮淘汰一半。普通直接设计不强制随机化。

```bash
# 标准模式的完整示例：文档/设计工件可直接作为 workbook 的 content 或 location
python scripts/design_audit.py --spec examples/general_design_spec.json --workbook examples/general_design_workbook.json --through handoff

# 单方案轻量设计，不需要大候选池或伪造竞品研究
python scripts/design_audit.py --spec examples/quick_design_spec.json --workbook examples/quick_design_workbook.json --through handoff
```

`structure_pass=true` 只表示**声明式结构与追踪关系完整**；`verification_status=incomplete` 表示还有未执行的验收，**不能冒充设计通过真实验证**。详见 `references/DESIGN_WORKFLOW.md` 和 `references/DELIVERY_CONTRACT.md`。

## 可选：独立随机种子驱动的多候选探索

**核心不变量：一个种子对应一条探索路径。** 发散任务至少抽取 **64 个独立且不重复的种子**，每个种子必须对应一条真实创意候选。每轮恰好淘汰一半，直到最终目标数；不能对齐时提高起始种子数，例如目标3个方案时使用96个种子，而不是64个。每批32条只是处理批次，种子彼此独立。保存 `plan.json` 才能完整重放。

| 最终目标 | 默认独立种子 | 逐轮存活 |
| --- | ---: | --- |
| 1 | 64 | 32 → 16 → 8 → 4 → 2 → 1 |
| 3 | 96 | 48 → 24 → 12 → 6 → 3 |
| 4 | 64 | 32 → 16 → 8 → 4 |
| 20 | 80 | 40 → 20 |

显式指定更大数量时，必须仍可逐轮精确减半至最终目标，例如 `--pool-size 256`、目标4时为 `256→128→64→32→16→8→4`。如果合规候选不足某轮的应保留数量，选拔失败并报告缺口，不能补造方案。

## 需求访谈（新）

在大规模发散之前核对关键设计信息，不自动假设“4组”等于“四组各5张”，也不把“最多7个新增属性”擅自解释为“禁止新增属性”。

```bash
python scripts/brief_gate.py --spec examples/cards_brief_missing.json --max-questions 1
```

只向用户询问当前最关键的一项；用户回答后再更新 brief。若用户明确委托自行决定，记录该授权再继续。`scripts/brief_gate.py` 仅检查 Agent 提供的事实与来源声明，不具备自主理解用户意图的能力。

## 256 → 4 示例

```bash
# 独立抽取256个随机种子、建立256条一对一绑定的路径清单和八个批次
python scripts/seed_ideation.py plan --spec examples/four_ideas_funnel.json --wildness 5 > plan.json

# 从 plan.json 中读取该批的32个独立种子，逐一生成可复现的路线
python scripts/seed_ideation.py batch --plan plan.json --spec examples/four_ideas_funnel.json --start 1 --format json > batch1.json
# 同样生成 --start 33,65,97,129,161,193,225

# Agent 根据每个 route 生成真实的短构想，逐条审查并记录到 pool.json
# 硬性条件不合格或未核实的方案计入第一轮淘汰，不能临时降低每轮目标数量
python scripts/funnel_select.py --spec examples/four_ideas_funnel.json --plan plan.json --candidates pool.json --output selection_report.json

# 逐轮淘汰一半：256→128→64→32→16→8→4，然后扩写四个胜出方案
python scripts/seed_ideation.py validate --spec examples/four_ideas_funnel.json --candidates final.json
```

`plan` 为每条路径生成**一个独立种子**，`batch` 使用该路径自己的种子产生路线，但**不自动撰写 256 个完整方案**。Agent 必须按批次真实创作候选、给出要求逐条核查与证据后才能声称探索了对应数量。筛选脚本会拒绝硬约束失败、未验证或缺少证据的项目，并按声明的机制标签做去重与多样性重排；无法自动证明语义上的真实合规或创新质量。

## 单条路径重放与向后兼容

```bash
# 仅重放清单中的第35条路径
python scripts/seed_ideation.py replay --spec examples/four_ideas_funnel.json --plan plan.json --start 35 --format json
# 也可用一条具体的种子单独重放；不会额外派生更多路径
python scripts/seed_ideation.py replay --spec examples/four_ideas_funnel.json --seed K7M2-8QVA-T3XP-H6RD --format json
# 生成最小64条独立路径（目标4），不能少于64个
python scripts/seed_ideation.py new --request "设计四种产品概念" --count 64 --format json
```

v1.6 是此前的独立种子行为修正：不再接受旧版 `plan --seed` 或 `batch --seed` 约定；旧版单主种子计划需要重新生成，不能将一条旧种子假装成多个独立种子。

## 预算与退出规则

发散式筛选固定下限64个独立种子，并采用精确对半淘汰；如果预算不允许完成至少64条真实候选，应使用 `direct` 直接设计工作流，而不是伪称已执行完整随机漏斗。筛选必须配合种子清单 `--plan`，且全部预定候选都真实记录。方案数量不足则如实报告，必要时重新开始另一轮完整的探索。

## 测试

```bash
python -m unittest discover -s tests -v
```

查看 `SKILL.md`、`references/DESIGN_WORKFLOW.md`、`references/DELIVERY_CONTRACT.md`、`references/FUNNEL.md` 与 `references/SPEC.md` 获取工作流、验证边界和 JSON 格式。
