# 全枚举验证与搜索算法修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复直接确认集合全枚举排名错误，实际完成 16 目标候选验证，明确默认重建搜索与全局候选最优之间的差距。

**Architecture:** `exact.py` 负责枚举和统一归一化，`experiments.py` 负责输出摘要和 Top 表，问题2推荐从枚举或候选池中读取。重建搜索只作为启发式候选生成器，不再单独承担最优性证明。

**Tech Stack:** Python 3.11, bitmask enumeration, `objective.py`, JSON/CSV, `pytest`.

---

## 1. 覆盖问题

- C-03：默认搜索算法存在局部陷阱。
- C-07：全枚举验证没有完成，且现有枚举排名代码有错误。
- M-11：接受准则没有直接优化论文定义的目标。
- M-12：全枚举耗时估算不能替代实际验证。

## 2. 文件清单

修改：

- `c_uav_inspection/exact.py`
- `c_uav_inspection/experiments.py`
- `c_uav_inspection/problem2.py`
- `tests/test_exact.py`
- `tests/test_experiments.py`
- `report/c_uav_inspection_paper.md`

输出：

- `outputs/c_uav_inspection/problem2_exact_summary.json`
- `outputs/c_uav_inspection/problem2_exact_top.csv`
- `working/artifacts/review-remediation/05-exact-tests.txt`
- `working/artifacts/review-remediation/05-exact-runtime.txt`

## 3. 修复归一化排名 bug

- [ ] **Step 1: 删除单元素归一化**

当前错误模式：

```python
rebuild_eval_list = _with_normalized_objectives([rebuild_eval])
rebuild_eval = rebuild_eval_list[0]
```

该写法会让重建解在单元素列表中归一化目标恒为 0。改为：

```python
scored_evaluations = _with_normalized_objectives(evaluations)
lookup = {
    tuple(ev.direct_nodes): ev
    for ev in scored_evaluations
    if ev.feasible
}
rebuild_eval = lookup.get(tuple(rebuild_direct))
```

若重建解不在枚举结果中，抛出错误，因为同一 `_rebuild_for_direct_set` 应该能复现该集合：

```python
if rebuild_eval is None:
    raise RuntimeError(
        f"Rebuild direct set {rebuild_direct} not found in enumeration results"
    )
```

- [ ] **Step 2: 排名必须按精确集合匹配**

`_find_rank_by_time` 和 `_find_rank_by_obj` 不能只用阈值比较找到“第一个不小于目标值”的位置。改为：

```python
def _find_rank_by_direct_nodes(
    ranked: list[DirectSetEvaluation],
    direct_nodes: tuple[int, ...],
) -> int:
    for idx, ev in enumerate(ranked, start=1):
        if tuple(ev.direct_nodes) == tuple(direct_nodes):
            return idx
    return len(ranked) + 1
```

这样同分或浮点接近时不会把别的候选当成重建解排名。

## 4. 全枚举输出

- [ ] **Step 3: 固定 `problem2_exact_summary.json` 字段**

JSON 必须包含：

```json
{
  "total_subsets": 65536,
  "feasible_subsets": 0,
  "runtime_s": 0.0,
  "k": 4,
  "direct_threshold_multiplier": 1.0,
  "allow_split_hover": true,
  "best_by_closed_loop": {},
  "best_by_objective": {},
  "rebuild_solution": {},
  "rebuild_time_rank": 0,
  "rebuild_time_gap_s": 0.0,
  "rebuild_time_gap_pct": 0.0,
  "rebuild_objective_rank": 0,
  "rebuild_objective_gap": 0.0
}
```

实际运行时 `feasible_subsets`、runtime 和候选内容写真实值。

- [ ] **Step 4: 固定 `problem2_exact_top.csv` 字段**

字段：

```text
rank_by_time
rank_by_objective
direct_nodes
feasible
closed_loop_time_s
uav_phase_time_s
ground_review_time_s
manual_count
weighted_manual_cost
direct_confirm_count
total_energy_j
load_std_s
route_count
normalized_objective
```

该 CSV 中的 `normalized_objective` 必须使用全部可行枚举候选的统一 bounds，不能对 Top-N 重新归一化。

## 5. 性能策略

- [ ] **Step 5: 缓存重复计算**

如果全枚举耗时过长，优先做以下优化：

1. 按 `direct_nodes` 缓存 `_hover_requirements_for_direct_set`。
2. 对 `solve_ground_tsp` 按 `manual_nodes` 缓存。
3. 对不可行原因进行短路，例如单目标直接确认已经超过单趟能耗上限。

不得用抽样替代全枚举输出。可以在论文中同时给出运行时间，但不能把运行时间估算写成验证结果。

## 6. 重建搜索定位

- [ ] **Step 6: 将默认重建搜索降级为启发式候选**

论文表述改为：

```text
重建搜索用于快速生成高质量候选。由于接受链具有路径依赖，最终推荐还需在统一候选集或全枚举结果中复核。
```

如果 `manual_reduction_time_tolerance=1.10` 或全直接确认明显优于默认 `1.03`，论文必须如实报告。

## 7. 测试

- [ ] **Step 7: 单元素归一化回归测试**

在 `tests/test_exact.py` 增加：

```python
def test_rebuild_objective_rank_uses_enumeration_bounds(problem_data):
    result = enumerate_direct_confirm_sets(
        problem_data,
        k=problem_data.params.k_max,
        direct_threshold_multiplier=1.0,
        top_n=5,
    )
    assert result.rebuild_solution is not None
    assert result.rebuild_solution.normalized_objective != 0.0 or result.rebuild_objective_rank == 1
```

该测试含义：重建方案只有在确实目标排名第一时才可能为 0；不能因为单元素归一化而恒为 0。

- [ ] **Step 8: 全枚举输出测试**

```python
def test_expensive_experiment_writes_exact_files(tmp_path, data_path):
    run_all_experiments(data_path, tmp_path, include_expensive=True)
    assert (tmp_path / "problem2_exact_summary.json").exists()
    assert (tmp_path / "problem2_exact_top.csv").exists()
```

## 8. 运行命令

先跑快速测试：

```bash
.venv/bin/python -m pytest tests/test_exact.py tests/test_experiments.py -q \
  | tee working/artifacts/review-remediation/05-exact-tests.txt
```

再跑全枚举并记录耗时：

```bash
/usr/bin/time -p .venv/bin/python - <<'PY' 2>&1 | tee working/artifacts/review-remediation/05-exact-runtime.txt
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments

run_all_experiments(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
    include_expensive=True,
)
PY
```

## 9. 验收标准

1. `problem2_exact_summary.json` 和 `problem2_exact_top.csv` 实际存在。
2. `total_subsets == 65536`。
3. `rebuild_objective_rank` 使用全枚举统一归一化结果。
4. 论文不再用“估算 128.5 分钟”替代全枚举验证。
5. 默认重建搜索若不是第一名，论文明确给出排名和差距。
