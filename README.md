# Seeded Ideation v1.4 | 需求驱动的大候选池随机创意 Skill

**核心目标：先产生大量简短、真正不同的方案，再淘汰不符合用户需求的内容，从合格者中选出最有价值、互有差异的结果。**

该技能适用于游戏、软件、界面、服务、文案等，不预设保守创新或颠覆式创新。用户的本次要求决定边界。随机种子只负责为探索提供可追溯的外部扰动。

## 安装

解压 `seeded-ideation` 至 Agent 支持的 skills 目录，例如 `%USERPROFILE%\.codex\skills\seeded-ideation\`。Python 3.9+，无第三方依赖。

## 需求访谈（新）

在大规模发散之前核对关键设计信息，不自动假设“4组”等于“四组各5张”，也不把“最多7个新增属性”擅自解释为“禁止新增属性”。

```bash
python scripts/brief_gate.py --spec examples/cards_brief_missing.json --max-questions 1
```

只向用户询问当前最关键的一项；用户回答后再更新 brief。若用户明确委托自行决定，记录该授权再继续。`scripts/brief_gate.py` 仅检查 Agent 提供的事实与来源声明，不具备自主理解用户意图的能力。

## 256 → 4 示例

```bash
# 获得包含随机种子的计划和八个批次
python scripts/seed_ideation.py plan --spec examples/four_ideas_funnel.json --wildness 5 > plan.json

# 从 plan.json 中读取 seed，逐批生成可复现的创意路线
python scripts/seed_ideation.py batch --seed 'K7M2-8QVA-T3XP-H6RD' --spec examples/four_ideas_funnel.json --start 1 --format json > batch1.json
# 同样生成 --start 33,65,97,129,161,193,225

# Agent 根据每个 route 生成真实的短构想，逐条审查并记录到 pool.json
# 硬性条件不合格或未核实的方案，在此阶段淘汰
python scripts/funnel_select.py --spec examples/four_ideas_funnel.json --candidates pool.json --output selection_report.json

# 将四个胜出方案扩写，附上要求的变体，并复查完整结果
python scripts/seed_ideation.py validate --spec examples/four_ideas_funnel.json --candidates final.json
```

`plan` 和 `batch` **只生成种子路线，不自动撰写 256 个完整方案**。Agent 必须按批次真实创作候选、给出要求逐条核查与证据后才能声称探索了对应数量。筛选脚本会拒绝硬约束失败、未验证或缺少证据的项目，并按声明的机制标签做去重与多样性重排；无法自动证明语义上的真实合规或创新质量。

## 不必永远 256 候选

用户需要快速建议时可用较小候选池；复杂创新任务可以加大倍数。候选池大小、批次、分阶段筛选尺度须服从时间与计算预算。如未足量生成，应如实说明而不能把路线数量冒充方案数量。

## 测试

```bash
python -m unittest discover -s tests -v
```

查看 `SKILL.md`、`references/FUNNEL.md` 与 `references/SPEC.md` 获取算法边界和候选 JSON 格式。
