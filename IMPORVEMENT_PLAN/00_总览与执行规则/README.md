# C题审查问题修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `PROBLEMS.md` 中的 SCI 级审查问题转化为按依赖链执行的完整修复路线。

**Architecture:** 先固定数据口径，再重构模型与评价体系，随后修正问题1、问题2、全枚举、实验、论文和测试。每一步只在通过自身验收后进入下一步，避免论文数字基于过期结果。

**Tech Stack:** Python 3.11, `openpyxl`, `pytest`, `matplotlib`, standard library `csv/json/dataclasses/itertools`, Markdown, `build_paper.py`.

---

## 1. 输入与输出

输入：

- `PROBLEMS.md`：审查问题清单。
- `2026同济数学建模竞赛赛题/2026C数据.xlsx`：原始数据。
- `c_uav_inspection/`：当前求解代码。
- `tests/`：当前测试。
- `report/c_uav_inspection_paper.md` 与 `report/c_uav_inspection_results.md`：论文源文本。
- `outputs/c_uav_inspection/`：当前实验输出。

输出：

- 修正后的代码、测试和实验输出。
- 修正后的论文 Markdown 与由脚本生成的 Word。
- 每一步的执行记录和测试结果。

## 2. 审查项分组

### 2.1 致命问题

| 编号 | 根因类别 | 处理步骤 |
|---|---|---|
| C-01 | 推荐方案不是当前模型下最优或稳健方案 | 04, 05 |
| C-02 | 全部直接确认被误称为能耗不可行 | 04, 07 |
| C-03 | 默认搜索陷入局部路径依赖 | 05 |
| C-04 | 可拆分推荐与不可拆分对照冲突 | 04 |
| C-05 | `ManualPoints` 与 `NodeData` 服务时间不一致 | 01 |
| C-06 | 推荐方案地面时间拆分写错 | 07 |
| C-07 | 全枚举验证缺失且排名代码有 bug | 05 |
| C-08 | 形式化优化模型不完整 | 02 |
| C-09 | 归一化目标不能跨实验推荐 | 02 |
| C-10 | 问题1时间优先 DP 是受限模型 | 03 |
| C-11 | 高优先级早完成性未建模 | 03 |
| C-12 | 能量敏感性解释错误 | 06, 07 |

### 2.2 主要问题

| 编号 | 根因类别 | 处理步骤 |
|---|---|---|
| M-01 | LPT 排序口径错误 | 03 |
| M-02 | 负载标准差未统计空闲无人机 | 03 |
| M-03 | 问题1能耗和负载权重实际为 0 | 02, 03 |
| M-04 | 推荐规模缺少成本和边际收益模型 | 03 |
| M-05 | “best route” 表述不严谨 | 03, 07 |
| M-06 | 地面 TSP 服务时间映射潜在错误 | 01 |
| M-07 | `.get(..., 0.0)` 掩盖数据缺失 | 01 |
| M-08 | 数据验证不完整 | 01 |
| M-09 | 运营时长约束未统一强制 | 03 |
| M-10 | 敏感性分析混入算法路径依赖 | 04, 06 |
| M-11 | 接受准则未直接优化论文定义的目标 | 02, 05 |
| M-12 | 全枚举耗时估算不能替代验证 | 05 |
| M-13 | 输出目录存在过期文件 | 06 |
| M-14 | 参考文献不足 | 07 |
| M-15 | 创新点表述偏强 | 07 |
| M-16 | 复杂度分析偏乐观 | 07 |
| M-17 | 缺少复现入口 | 06, 07 |
| M-18 | 测试过慢且全量测试不稳定 | 08 |

### 2.3 写作问题

| 编号 | 处理步骤 |
|---|---|
| W-01, W-02, W-03, W-04, W-05, W-06, W-07 | 07 |
| W-08 | 06, 07 |

## 3. 执行纪律

- [ ] **Step 1: 固定执行分支和状态**

运行：

```bash
git status --short
```

预期：只看到当前任务相关改动，未跟踪的 `PROBLEMS.md` 可保留但不得误删。

- [ ] **Step 2: 建立执行记录目录**

运行：

```bash
mkdir -p working/artifacts/review-remediation
```

记录每一步的测试输出到该目录，例如：

```bash
.venv/bin/python -m pytest tests/test_data.py -q \
  | tee working/artifacts/review-remediation/01-data-tests.txt
```

- [ ] **Step 3: 按顺序执行步骤 01 到 08**

不得跳过数据步骤直接改论文。若步骤 01 改变服务时间来源，步骤 02 到 07 的全部数值必须重算。

- [ ] **Step 4: 每一步结束时检查文件状态**

运行：

```bash
git diff --stat
git status --short
```

验收：当前步骤的改动文件与该步骤 README 中的文件清单一致。

## 4. 结果口径

所有论文表格使用如下优先级：

1. `outputs/c_uav_inspection/*.json`
2. `outputs/c_uav_inspection/*.csv`
3. 自动同步脚本生成的 Markdown 表格

禁止直接从人工记忆或旧 Word 中抄数字。

## 5. 推荐方案口径

最终推荐方案必须满足以下任一条件：

1. 在统一候选集中按固定业务权重最优。
2. 位于帕累托前沿，且论文明确说明选择原因。
3. 满足预先声明的硬约束，例如闭环时间上限、航次数上限、总能耗预算或人工复核上限。

如果全直接确认在运营时长和单趟能耗上可行，论文必须承认其可行性。是否不推荐它，只能基于能耗、航次数、负载、成本或业务风险等明确准则。
