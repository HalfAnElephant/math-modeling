# 问题一时间优先与高优先级早完成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复问题1只做受限时间优先、未建模高优先级早完成、LPT 与负载统计口径不严谨的问题。

**Architecture:** 保留当前 packed 与 time-priority DP 作为启发式候选，但明确二者不是完整原问题全局最优。新增目标完成时刻、加权完成时刻和边际收益分析，使推荐无人机规模有业务含义。

**Tech Stack:** Python 3.11, `problem1.py`, `problem1_time.py`, `model.py`, `experiments.py`, `pytest`.

---

## 1. 覆盖问题

- C-10：问题1“时间优先 DP”不是题目完整问题的最优模型。
- C-11：高优先级早完成性没有真正建模。
- M-01：LPT 调度实现不是标准 LPT。
- M-02：负载标准差未统计空闲无人机。
- M-03：问题1能耗和负载权重实际为 0。
- M-04：边际收益递减和推荐规模缺少成本模型。
- M-05：`problem1_time.py` 文档称“best route for every subset”不严谨。
- M-09：运营时长约束没有在所有求解入口统一强制。

## 2. 文件清单

修改：

- `c_uav_inspection/model.py`
- `c_uav_inspection/problem1.py`
- `c_uav_inspection/problem1_time.py`
- `c_uav_inspection/search.py`
- `c_uav_inspection/experiments.py`
- `tests/test_model.py`
- `tests/test_problem1.py`
- `tests/test_problem1_time.py`
- `tests/test_search.py`
- `tests/test_experiments.py`
- `report/c_uav_inspection_paper.md`

输出：

- `outputs/c_uav_inspection/problem1_packed_k_comparison.csv`
- `outputs/c_uav_inspection/problem1_time_priority_k_comparison.csv`
- `outputs/c_uav_inspection/problem1_priority_completion_k_comparison.csv`
- `outputs/c_uav_inspection/problem1_marginal_benefit.csv`

## 3. 负载统计修复

- [ ] **Step 1: 修改 `summarize_uav_solution` 支持总无人机数**

当前只统计有路线的无人机。新增参数：

```python
def summarize_uav_solution(
    routes: tuple[UAVRoute, ...] | list[UAVRoute],
    data: ProblemData,
    battery_swap_time_s: float,
    k: int | None = None,
) -> UAVSolutionSummary:
```

行为：

1. `k is None` 时保持兼容，只统计出现过的 `uav_id`。
2. `k` 给定时，`uav_work_times_s` 必须包含 `1..k`。
3. 未执行任务的无人机工作时长为 `0.0`。
4. `load_std_s` 用包含空闲无人机的工作时长计算。

测试：

```python
def test_summary_counts_idle_uavs_when_k_is_given(problem_data):
    route = UAVRoute(
        uav_id=1,
        sortie_id=1,
        node_sequence=(0, 1, 0),
        hover_times_s={1: problem_data.targets[0].base_hover_time_s},
    )
    summary = summarize_uav_solution([route], problem_data, 300.0, k=4)
    assert set(summary.uav_work_times_s) == {1, 2, 3, 4}
    assert summary.uav_work_times_s[2] == 0.0
    assert summary.load_std_s > 0.0
```

## 4. LPT 口径修复

- [ ] **Step 2: 按完整航次处理时间排序**

定位 `problem1.py` 或 `search.py` 中分配航次给 UAV 的逻辑。当前若按悬停总时长排序，改为：

```python
route_metrics = [(route, evaluate_uav_route(route, data).duration_s) for route in routes]
route_metrics.sort(key=lambda item: item[1], reverse=True)
```

分配给当前累计工作时间最短的 UAV。若同一无人机已有航次，累计工作时间要加换电时间：

```python
additional = duration_s
if assigned_routes[uav_id]:
    additional += battery_swap_time_s
```

## 5. 运营时长硬约束

- [ ] **Step 3: 在问题1所有入口检查运营时长**

`solve_problem1_for_k`、`solve_uav_hover_plan`、`solve_problem1_time_priority_for_k` 返回前必须检查：

```python
if summary.uav_phase_time_s > data.params.operating_horizon_s:
    raise InfeasibleError(
        f"UAV phase time {summary.uav_phase_time_s:.2f}s exceeds "
        f"operating horizon {data.params.operating_horizon_s:.2f}s"
    )
```

实验函数捕获不可行并写 `feasible=False`，不要静默输出超时方案。

## 6. 高优先级早完成性

- [ ] **Step 4: 增加目标完成时刻计算**

新增函数，建议放在 `model.py`：

```python
def compute_target_completion_times(
    routes: tuple[UAVRoute, ...] | list[UAVRoute],
    data: ProblemData,
    battery_swap_time_s: float,
) -> dict[int, float]:
```

计算规则：

1. 每架无人机按 `sortie_id` 排序。
2. 同一无人机第 2 趟及以后在前一趟结束后加一次换电时间。
3. 沿 `node_sequence` 累加飞行时间。
4. 到达目标后累加该目标在本趟的悬停时间。
5. 对可拆分悬停，目标完成时刻是累计悬停达到 `base_hover_time_s` 的最早时刻。

如果目标未达到基础悬停，抛出 `ValueError`。

- [ ] **Step 5: 增加加权完成时刻指标**

新增函数：

```python
def weighted_priority_completion_time(
    completion_times: Mapping[int, float],
    data: ProblemData,
) -> float:
    weight_by_node = {t.node_id: t.priority_weight for t in data.targets}
    return sum(weight_by_node[nid] * completion_times[nid] for nid in completion_times)
```

实验输出字段：

```text
weighted_completion_time_s
max_priority3_completion_time_s
mean_priority3_completion_time_s
```

## 7. 问题1候选与表述修正

- [ ] **Step 6: 修正 `problem1_time.py` 文档**

将“best route for every subset”改为：

```text
heuristic route candidate for every subset
```

论文中写：

```text
时间优先子集划分是单趟、不可拆分归属的启发式验证，用于评估多机并行上界潜力；它不等同于含多趟、可拆分悬停的完整原问题精确最优。
```

- [ ] **Step 7: 保留 packed 与 time-priority 两类候选**

输出两个表：

1. `problem1_packed_k_comparison.csv`：当前可拆分装箱启发式。
2. `problem1_time_priority_k_comparison.csv`：时间优先子集划分启发式。

两个表都要包含：

```text
k, feasible, solver_name, uav_phase_time_s, weighted_completion_time_s,
total_energy_j, load_std_s, route_count, max_route_energy_j
```

## 8. 边际收益与推荐规模

- [ ] **Step 8: 生成 `problem1_marginal_benefit.csv`**

字段：

```text
k, uav_phase_time_s, improvement_from_previous_s,
improvement_from_previous_pct, weighted_completion_time_s,
weighted_completion_improvement_s, route_count, total_energy_j,
load_std_s, recommended_by_time, recommended_by_cost_rule
```

推荐规则必须显式：

```text
若新增一架无人机带来的阶段时间改善比例低于 5%，且加权完成时刻改善比例低于 5%，则不再推荐继续增加。
```

如果数据表现为 `K=4` 明显更快，则推荐 `K=4`；如果 `K=3` 到 `K=4` 改善低于阈值，推荐 `K=3` 并说明成本阈值。

## 9. 测试

- [ ] **Step 9: 完成时刻测试**

```python
def test_completion_times_reach_base_hover(problem_data):
    sol = solve_problem1_for_k(problem_data, 4, problem_data.params.battery_swap_time_s)
    completion = compute_target_completion_times(
        sol.routes,
        problem_data,
        problem_data.params.battery_swap_time_s,
    )
    assert set(completion) == {t.node_id for t in problem_data.targets}
    assert all(v > 0.0 for v in completion.values())
```

- [ ] **Step 10: 问题1输出字段测试**

```python
def test_problem1_outputs_include_priority_completion(tmp_path, data_path):
    run_all_experiments(data_path, tmp_path, include_expensive=False)
    rows = list(csv.DictReader((tmp_path / "problem1_time_priority_k_comparison.csv").open()))
    assert "weighted_completion_time_s" in rows[0]
    assert "max_priority3_completion_time_s" in rows[0]
```

## 10. 运行命令

```bash
.venv/bin/python -m pytest tests/test_model.py tests/test_search.py tests/test_problem1.py tests/test_problem1_time.py tests/test_experiments.py -q \
  | tee working/artifacts/review-remediation/03-problem1-tests.txt
```

## 11. 验收标准

1. 负载标准差可选择统计空闲无人机，问题1实验必须传入 `k`。
2. LPT 按完整航次处理时间排序。
3. 问题1所有可行输出满足 `uav_phase_time_s <= operating_horizon_s`。
4. 论文包含高优先级早完成指标。
5. 推荐无人机规模有边际收益或成本规则，不再简单说“越多越好”或“2 架已经足够”。
