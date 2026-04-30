# 问题二直接确认候选集与帕累托推荐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复问题2推荐方案与可行候选冲突的问题，将全直接确认、仅基础巡检、可拆分/不可拆分、重建搜索和全枚举候选纳入统一推荐逻辑。

**Architecture:** 问题2先生成候选池，再做可行性过滤、帕累托筛选和推荐选择。论文中所有推荐结论都从候选池文件读取，不再从单个启发式输出直接得出。

**Tech Stack:** Python 3.11, `problem2.py`, `exact.py`, `objective.py`, `experiments.py`, CSV/JSON.

---

## 1. 覆盖问题

- C-01：推荐方案不是当前模型/代码下的最优或稳健方案。
- C-02：论文称“全部直接确认能耗不可行”，事实相反。
- C-04：可拆分推荐与不可拆分消融结论冲突。
- M-10：敏感性分析混入算法路径依赖。

## 2. 文件清单

修改：

- `c_uav_inspection/problem2.py`
- `c_uav_inspection/exact.py`
- `c_uav_inspection/objective.py`
- `c_uav_inspection/experiments.py`
- `tests/test_problem2.py`
- `tests/test_exact.py`
- `tests/test_experiments.py`
- `report/c_uav_inspection_paper.md`
- `report/c_uav_inspection_results.md`

输出：

- `outputs/c_uav_inspection/problem2_candidate_pool.csv`
- `outputs/c_uav_inspection/problem2_pareto_front.csv`
- `outputs/c_uav_inspection/problem2_baseline_comparison.csv`
- `outputs/c_uav_inspection/problem2_all_direct_confirm_baseline.json`
- `outputs/c_uav_inspection/problem2_split_hover_ablation.csv`
- `outputs/c_uav_inspection/recommended_solution.json`

## 3. 必纳入候选

- [ ] **Step 1: 固定问题2候选类型**

候选池必须至少包含：

1. `base_only`：全部目标基础巡检，全部人工复核。
2. `all_direct_confirm`：16 个目标全部无人机直接确认。
3. `rebuild_default`：当前默认重建搜索。
4. `rebuild_tolerance_1.00`、`1.03`、`1.05`、`1.10`：接受准则敏感性候选。
5. `split_hover_true`：可拆分悬停方案。
6. `split_hover_false`：不可拆分悬停方案。
7. `exact_best_time`：全枚举闭环时间最优方案，步骤 05 生成。
8. `exact_best_objective`：全枚举统一候选池评分最优方案，步骤 05 生成。

## 4. 全直接确认基准

- [ ] **Step 2: 增加全直接确认构造函数**

新增或公开函数：

```python
def solve_all_direct_confirm_baseline(
    data: ProblemData,
    k: int,
    direct_threshold_multiplier: float = 1.0,
    allow_split_hover: bool = True,
) -> JointSolution:
    direct_nodes = tuple(t.node_id for t in data.targets)
    solution = _rebuild_for_direct_set(
        data, k, direct_nodes, direct_threshold_multiplier,
        allow_split_hover=allow_split_hover,
    )
    if solution is None:
        raise InfeasibleError("All-direct-confirm baseline is infeasible")
    return solution
```

验收：若当前数据下全直接确认可行，输出必须记录：

```text
direct_confirm_count = 16
manual_count = 0
ground_review_time_s = 0
```

论文中禁止写“能耗不可行”。正确表述示例：

```text
全部直接确认在单趟能耗和运营时长约束下可行，但会显著增加总能耗、航次数和无人机负载，因此是否推荐取决于能耗预算与运维成本。
```

## 5. 候选池字段

- [ ] **Step 3: 生成 `problem2_candidate_pool.csv`**

每行字段：

```text
candidate_id
source
k
direct_threshold_multiplier
allow_split_hover
manual_reduction_time_tolerance
feasible
infeasible_reason
direct_confirmed_nodes
manual_target_nodes
direct_confirm_count
manual_count
weighted_manual_cost
uav_phase_time_s
ground_review_time_s
closed_loop_time_s
total_energy_j
load_std_s
route_count
max_route_energy_j
operating_horizon_s
within_operating_horizon
notes
```

所有集合字段使用空格分隔的稳定升序字符串，例如 `"1 4 6 7 10 12 16"`。

## 6. 帕累托前沿

- [ ] **Step 4: 生成 `problem2_pareto_front.csv`**

从候选池中过滤：

```text
feasible == True
within_operating_horizon == True
```

最小化指标：

```text
closed_loop_time_s
manual_count
weighted_manual_cost
total_energy_j
route_count
load_std_s
```

输出字段在候选池基础上增加：

```text
pareto_rank
recommendation_score
recommendation_reason
```

`pareto_rank` 第一版可全部填 1，表示非支配前沿；如果后续分层剥离前沿，可使用 1, 2, 3。

## 7. 推荐规则

- [ ] **Step 5: 固定推荐选择函数**

新增：

```python
def choose_recommended_problem2_candidate(
    pareto_rows: list[dict[str, Any]],
) -> dict[str, Any]:
```

默认业务规则：

1. 必须在帕累托前沿。
2. 必须满足运营时长。
3. 若存在 `closed_loop_time_s <= 2600` 且 `manual_count <= 2` 的候选，优先按 `weighted_manual_cost`、`total_energy_j`、`route_count` 排序。
4. 否则按固定权重评分排序：

```python
weights = {
    "closed_loop_time_s": 0.40,
    "weighted_manual_cost": 0.20,
    "manual_count": 0.15,
    "total_energy_j": 0.10,
    "route_count": 0.10,
    "load_std_s": 0.05,
}
```

评分 bounds 来自 `pareto_rows`，不是单个实验表。

推荐理由必须写入 `recommended_solution.json`：

```json
{
  "candidate_id": "pareto_001",
  "selection_rule": "pareto_weighted_score",
  "recommendation_reason": "位于帕累托前沿，并在固定权重评分下排名第一"
}
```

## 8. 可拆分/不可拆分冲突处理

- [ ] **Step 6: 修改可拆分消融解释**

如果不可拆分方案在闭环时间、总能耗和归一化分数上优于可拆分方案，论文必须承认，并按推荐规则选择不可拆分或解释业务约束。

禁止写法：

```text
可拆分方案综合更优。
```

当数据不支持时，改为：

```text
在当前权重和候选池下，不可拆分方案位于更优位置；可拆分机制仍作为模型能力保留，但不是本轮推荐解。
```

## 9. 测试

- [ ] **Step 7: 测试全直接确认基准**

```python
def test_all_direct_confirm_baseline_is_represented(problem_data):
    sol = solve_all_direct_confirm_baseline(problem_data, problem_data.params.k_max)
    assert len(sol.closed_loop.direct_confirmed_nodes) == len(problem_data.targets)
    assert sol.closed_loop.manual_count == 0
    assert sol.closed_loop.ground_review_time_s == 0.0
```

- [ ] **Step 8: 测试候选池包含关键方案**

```python
def test_problem2_candidate_pool_contains_required_sources(tmp_path, data_path):
    run_all_experiments(data_path, tmp_path, include_expensive=False)
    rows = list(csv.DictReader((tmp_path / "problem2_candidate_pool.csv").open()))
    sources = {row["source"] for row in rows}
    assert "base_only" in sources
    assert "all_direct_confirm" in sources
    assert "rebuild_default" in sources
    assert "split_hover_false" in sources
```

## 10. 运行命令

```bash
.venv/bin/python -m pytest tests/test_problem2.py tests/test_experiments.py -q \
  | tee working/artifacts/review-remediation/04-problem2-candidates-tests.txt
```

重跑常规候选：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments

run_all_experiments(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
    include_expensive=False,
)
PY
```

## 11. 验收标准

1. `problem2_candidate_pool.csv` 包含全直接确认候选。
2. 全直接确认可行时，论文承认其可行性。
3. `problem2_pareto_front.csv` 由统一候选池生成。
4. `recommended_solution.json` 包含推荐规则和推荐理由。
5. 论文不再把默认重建搜索链末端自动当作推荐方案。
