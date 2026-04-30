# 形式化模型与评价体系重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐数学优化模型变量与约束，重构多目标评价体系，使推荐方案在统一候选集内可解释、可复核。

**Architecture:** 论文中给出完整变量、目标和约束；代码中区分“表内展示用归一化”和“推荐用统一候选集评价”。推荐决策优先使用帕累托前沿和固定业务规则，避免跨实验 min-max 分数误用。

**Tech Stack:** Python 3.11, dataclasses, `objective.py`, CSV/JSON candidate pools, Markdown formula.

---

## 1. 覆盖问题

- C-08：形式化优化模型不完整。
- C-09：归一化目标不能作为跨实验推荐依据。
- M-03：问题1能耗和负载权重实际为 0。
- M-11：接受准则没有直接优化论文定义的目标。

## 2. 文件清单

修改：

- `c_uav_inspection/objective.py`
- `c_uav_inspection/model.py`
- `c_uav_inspection/problem2.py`
- `c_uav_inspection/exact.py`
- `c_uav_inspection/experiments.py`
- `tests/test_objective.py`
- `tests/test_model.py`
- `tests/test_problem2.py`
- `tests/test_exact.py`
- `report/c_uav_inspection_paper.md`

输出：

- `outputs/c_uav_inspection/problem2_candidate_pool.csv`
- `outputs/c_uav_inspection/problem2_pareto_front.csv`
- `outputs/c_uav_inspection/recommended_solution.json`

## 3. 论文模型补齐

- [ ] **Step 1: 定义集合与索引**

在论文模型章节加入：

```text
S = {1,...,16}: 巡检目标集合
V = {0} ∪ S: 无人机节点集合
K = {1,...,K}: 无人机集合
R_k: 无人机 k 可执行航次集合
M: 物业人工复核点集合
```

- [ ] **Step 2: 定义决策变量**

必须包含：

```text
x_{krij} ∈ {0,1}: 无人机 k 第 r 趟是否从 i 飞到 j
z_{krs} ∈ {0,1}: 无人机 k 第 r 趟是否访问目标 s
u_{krs} ≥ 0: 无人机 k 第 r 趟在目标 s 的悬停时间
q_s ∈ {0,1}: 目标 s 是否由无人机直接确认
m_s ∈ {0,1}: 目标 s 是否需要物业复核
a_{kr} ∈ {0,1}: 无人机 k 第 r 趟是否启用
C_s ≥ 0: 目标 s 基础巡检完成时刻
L_k ≥ 0: 无人机 k 总作业时长
T_u ≥ 0: 无人机阶段完成时间
T_g ≥ 0: 地面复核阶段时间
```

- [ ] **Step 3: 定义关键约束**

论文必须写出：

```text
∑_{k,r} u_{krs} ≥ b_s                         ∀s∈S
∑_{k,r} u_{krs} ≥ h_s q_s                     ∀s∈S
m_s = 1 - q_s                                 ∀s∈S
u_{krs} ≤ H_s z_{krs}                         ∀k,r,s
∑_{j∈V} x_{kr0j} = a_{kr}                     ∀k,r
∑_{i∈V} x_{kri0} = a_{kr}                     ∀k,r
∑_{i∈V} x_{kris} = z_{krs}                    ∀k,r,s
∑_{j∈V} x_{krsj} = z_{krs}                    ∀k,r,s
∑_{(i,j)} e^f_{ij}x_{krij} + P_h∑_s u_{krs} ≤ E_max a_{kr}
L_k = ∑_r route_time_{kr} + τ_b∑_r transition_{kr}
T_u ≥ L_k                                     ∀k
T_u ≤ H_oper
```

子环消除可用 MTZ 或说明算法用路径构造保证单条路线连通。若不写完整 MILP 求解器，论文必须表述为“形式化约束定义 + 启发式求解框架”，不能声称精确求解完整 MILP。

## 4. 评价体系重构

- [ ] **Step 4: 区分三类指标**

代码和论文统一使用：

1. 硬约束：单趟能耗、运营时长、数据完整性。
2. 主要目标：闭环时间、问题1阶段时间、加权完成时刻。
3. 辅助目标：人工点数、加权人工代价、总能耗、航次数、负载标准差。

- [ ] **Step 5: 修改推荐准则**

问题2推荐不再使用不同实验表内各自 min-max 的分数。推荐准则固定为：

```text
先筛选可行候选；
再剔除被支配候选形成帕累托前沿；
若有业务硬阈值，先按阈值过滤；
最终在同一个候选池内按固定权重评分或选择解释性折中点。
```

候选 A 支配候选 B 的定义：

```text
A 在 closed_loop_time_s、manual_count、weighted_manual_cost、total_energy_j、route_count、load_std_s 上全部不劣于 B，
且至少一个指标严格优于 B。
```

- [ ] **Step 6: 在 `objective.py` 增加帕累托函数**

新增：

```python
def is_dominated(
    candidate: Mapping[str, float],
    other: Mapping[str, float],
    minimize_terms: Sequence[str],
) -> bool:
    no_worse = all(other[t] <= candidate[t] for t in minimize_terms)
    strictly_better = any(other[t] < candidate[t] for t in minimize_terms)
    return no_worse and strictly_better


def pareto_front(
    rows: Sequence[Mapping[str, float]],
    minimize_terms: Sequence[str],
) -> list[Mapping[str, float]]:
    result = []
    for row in rows:
        if not any(is_dominated(row, other, minimize_terms) for other in rows):
            result.append(row)
    return result
```

测试应覆盖：完全相同候选不互相支配；一个指标更差但另一个更好时都保留；全指标不劣且至少一个更优时剔除。

- [ ] **Step 7: 增加固定候选池评分**

在 `objective.py` 增加：

```python
def score_with_fixed_bounds(
    row: Mapping[str, float],
    bounds: Mapping[str, ObjectiveTermBounds],
    weights: Mapping[str, float],
) -> float:
    values = {name: float(row[name]) for name in weights}
    return weighted_normalized_objective(values, dict(bounds), weights)
```

要求：bounds 来自同一个候选池，不来自单个候选或不同实验表。

## 5. 问题1权重口径

- [ ] **Step 8: 修改问题1评价解释**

问题1论文中不能再写“同时关注时间、能耗、负载”却把能耗和负载权重设为 0。改成两层：

1. 主模型：优先最小化 `T_u` 和高优先级加权完成时刻。
2. 辅助报告：总能耗、负载标准差、航次数用于解释与推荐规模。

若保留归一化表格，必须说明：

```text
该归一化分数只用于同一表内展示，不作为跨表推荐依据。
```

## 6. 问题2接受准则调整

- [ ] **Step 9: 让搜索保留候选而不是只保留链末端**

修改 `solve_joint_problem_for_k` 或新增候选收集函数：

```python
def collect_rebuild_candidates_for_k(
    data: ProblemData,
    k: int,
    direct_threshold_multiplier: float,
    allow_split_hover: bool = True,
    manual_reduction_time_tolerance: float = 1.03,
) -> list[JointSolution]:
```

要求：

1. 记录空直接确认集。
2. 记录每次尝试加入节点后的可行候选。
3. 记录接受链候选。
4. 输出中包含 `direct_confirmed_nodes`，便于与全枚举比对。

推荐方案从候选池或全枚举池中选择，不从“最后一个被接受的当前解”自动产生。

## 7. 测试

- [ ] **Step 10: 测试帕累托前沿**

```python
def test_pareto_front_removes_dominated_rows():
    rows = [
        {"name": "a", "time": 10.0, "energy": 10.0},
        {"name": "b", "time": 12.0, "energy": 10.0},
        {"name": "c", "time": 9.0, "energy": 12.0},
    ]
    front = pareto_front(rows, ("time", "energy"))
    names = {r["name"] for r in front}
    assert names == {"a", "c"}
```

- [ ] **Step 11: 测试固定 bounds 不退化**

```python
def test_fixed_bounds_scoring_uses_shared_candidate_pool():
    bounds = {
        "time": ObjectiveTermBounds(10.0, 20.0),
        "energy": ObjectiveTermBounds(100.0, 200.0),
    }
    score = score_with_fixed_bounds(
        {"time": 15.0, "energy": 150.0},
        bounds,
        {"time": 0.5, "energy": 0.5},
    )
    assert score == 0.5
```

## 8. 运行命令

```bash
.venv/bin/python -m pytest tests/test_objective.py tests/test_model.py tests/test_problem2.py -q \
  | tee working/artifacts/review-remediation/02-objective-tests.txt
```

## 9. 验收标准

1. 论文模型章节包含弧变量、访问变量、悬停变量、直接确认变量、复核变量、能耗约束、运营时长约束和路径连通说明。
2. 问题2推荐方案来自统一候选池，不来自跨表 min-max。
3. `objective.py` 提供帕累托前沿函数并有测试。
4. 接受准则敏感性只能解释搜索行为，不能替代最终推荐依据。
