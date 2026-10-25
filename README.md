# Seeded Ideation

> A reusable design workflow for AI agents — from a clear brief to an auditable design, with optional seed-driven exploration.

[![Tests](https://github.com/coicy/seeded-ideation/actions/workflows/tests.yml/badge.svg)](https://github.com/coicy/seeded-ideation/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)

**Seeded Ideation** 是一个面向 AI Agent 的通用设计 Skill，帮助完成需求界定、方案探索、设计决策、详细规格、验证与交付。它适用于游戏机制、软件功能、用户界面、服务流程和内容创作等设计任务。

需要大量备选方案时，可以启用**独立种子探索**：每个随机种子对应一条独立路径，从至少 64 条路径开始，每轮淘汰一半，直到得到目标数量的方案。只需要直接改进一个设计时，不必运行随机漏斗。

## 核心特点

- **完整设计流程**：从问题、约束与目标出发，而不是直接生成随机点子。
- **按需发散**：支持 `quick`、`standard`、`rigorous` 三种工作深度；随机探索是可选分支。
- **每路径独立种子**：一条路径绑定一个种子；支持保存清单、批次生成与单路径重放。
- **逐轮筛选**：发散时不少于 64 条路径，并按照预先计算的配额逐轮保留一半。
- **需求与验证追踪**：区分硬约束、偏好、假设和测试结果，记录候选淘汰原因。

> **能力边界：** Python 脚本生成可追溯的种子、探索提示和结构化审查结果；**实际设计候选需要 Agent 创作和评估**。种子数量不等于已完成的设计数量，结构检查通过也不等于设计质量已得到验证。

## 适用场景

| 任务 | 建议方式 |
| --- | --- |
| 优化已有 UI、游戏规则或软件功能 | `direct`：分析现状，提出可执行的修改方案 |
| 比较不同设计思路 | `compare`：明确差异、取舍和验收标准 |
| 需要大量差异化创意 | 独立种子探索 + 分轮筛选 |
| 审核设计规格与验收记录 | `design_audit.py` 检查声明式追踪关系 |

## 快速开始

### 1. 作为 Codex Skill 使用

Codex 当前支持从 `$HOME/.agents/skills/` 读取用户级 Skill。将此仓库克隆为其中的独立目录（需要 Git）：

**macOS / Linux**

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/coicy/seeded-ideation.git "$HOME/.agents/skills/seeded-ideation"
```

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force "$HOME/.agents/skills" | Out-Null
git clone https://github.com/coicy/seeded-ideation.git "$HOME/.agents/skills/seeded-ideation"
```

安装后，在 Codex 中可以明确指定此 Skill，例如：

> 使用 `seeded-ideation` 为我的游戏设计 4 套机制差异明显的资源管理方案。先确认已有规则，保留硬性约束，采用独立种子探索，解释筛选依据，并给出可验证的最终规格。

其他支持 Agent Skills 格式的 Agent，可将仓库放入其对应的 Skills 目录。参见 [Codex Skill 文档](https://developers.openai.com/codex/skills)。

### 2. 直接使用 Python 工具

要求：Python 3.9+，不需要第三方 Python 依赖。

```bash
git clone https://github.com/coicy/seeded-ideation.git
cd seeded-ideation

# 生成探索计划，默认至少 64 个独立种子
python scripts/seed_ideation.py plan \
  --spec examples/four_ideas_funnel.json > plan.json

# 读取清单中第一批种子，为每条路径生成探索提示
python scripts/seed_ideation.py batch \
  --spec examples/four_ideas_funnel.json \
  --plan plan.json --start 1 --format json > batch_001.json
```

这两条命令会生成 **`plan.json`（种子清单与筛选轮次）** 和 **`batch_001.json`（第一批探索提示）**。它们**不会自动写出完整的设计方案**；应由 Agent 为每条路径撰写候选并记录评价，再使用筛选器。

## 工作方式

```text
用户目标与约束
      │
      ▼
需求界定 → 资料分析 → 方案设计 → 评估决策 → 详细规格 → 验证交付
                         │
                 需要发散时才启用
                         ▼
              64+ 个独立随机种子
                         ▼
              每个种子对应一条路径
                         ▼
                  Agent 创作候选
                         ▼
             硬约束核查、去重、评价
                         ▼
                 每轮淘汰 50%
                         ▼
                  最终设计方案
```

例如目标是 4 个方案，默认筛选路径为 **64 → 32 → 16 → 8 → 4**。目标是 3 个方案时，使用 **96 → 48 → 24 → 12 → 6 → 3**，以确保每轮精确对半。筛选失败或合规候选不足时，必须报告缺口，而不是虚构补足。

查看或重放某条已有路径：

```bash
python scripts/seed_ideation.py replay \
  --spec examples/four_ideas_funnel.json \
  --plan plan.json --start 35 --format json
```

完整的候选数据格式、`funnel_select.py` 操作方法及验证要求见 [筛选规范](references/FUNNEL.md) 和 [Skill 工作流](SKILL.md)。

## 文档与项目结构

| 位置 | 用途 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Agent 触发条件与完整执行要求 |
| [`references/DESIGN_WORKFLOW.md`](references/DESIGN_WORKFLOW.md) | 通用设计流程 |
| [`references/SPEC.md`](references/SPEC.md) | 需求规格与参数格式 |
| [`references/FUNNEL.md`](references/FUNNEL.md) | 独立种子、候选筛选与评价规则 |
| [`references/DELIVERY_CONTRACT.md`](references/DELIVERY_CONTRACT.md) | 设计交付与验收要求 |
| [`examples/`](examples/) | 可运行的示例需求与设计记录 |
| [`scripts/`](scripts/) | 规划、批处理、筛选与结构审查工具 |

## 测试与反馈

在仓库根目录运行：

```bash
python -m unittest discover -s tests -v
```

自动测试覆盖种子清单、独立路径、重放、逐轮配额和结构审查等**程序行为**；设计创意的实际价值仍需针对任务进行评估。

问题报告和改进建议可通过 [GitHub Issues](https://github.com/coicy/seeded-ideation/issues) 提交。维护者：[@coicy](https://github.com/coicy)。

## 许可证

仓库目前未提供 `LICENSE` 文件。**公开可见不等于已授予开源使用许可**；如需分发、复用或贡献代码，应先由维护者明确许可条款。
