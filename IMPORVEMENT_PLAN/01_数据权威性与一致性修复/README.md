# 数据权威性与一致性修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固定原始数据的权威读取口径，修复人工服务时间、人工点映射和矩阵完整性校验问题。

**Architecture:** `data.py` 负责读取并校验所有 Excel 工作表，`problem2.py` 只使用已经校验过的数据结构，不在求解阶段猜测服务时间。所有缺失或冲突数据必须显式报错或写入验证摘要。

**Tech Stack:** Python 3.11, `openpyxl`, dataclasses, `pytest`, JSON validation output.

---

## 1. 覆盖问题

本步骤覆盖：

- C-05：`ManualPoints` 与 `NodeData` 人工服务时间不一致，代码未处理。
- M-06：地面 TSP 服务时间映射存在潜在错误。
- M-07：`_direct_confirm_score` 使用 `.get(..., 0.0)` 掩盖数据缺失。
- M-08：数据验证不完整。

## 2. 数据口径决策

固定以下规则：

1. `NodeData` 是目标点属性表，负责目标编号、优先级、悬停需求和目标到人工点的映射。
2. `ManualPoints` 是物业复核点表，负责人工点坐标和人工现场服务时间。
3. 当 `NodeData.manual_service_time_s` 与 `ManualPoints.manual_service_time_s` 不一致时，地面复核时间以 `ManualPoints` 为准，同时在 `data_validation.json` 中记录差异。
4. 论文必须说明该口径：人工点服务时间来自专门的 `ManualPoints` 表，`NodeData` 中重复字段只用于冲突检查。

## 3. 文件清单

修改：

- `c_uav_inspection/data.py`
- `c_uav_inspection/problem2.py`
- `c_uav_inspection/experiments.py`
- `tests/test_data.py`
- `tests/test_problem2.py`
- `report/c_uav_inspection_results.md`
- `report/c_uav_inspection_paper.md`

输出：

- `outputs/c_uav_inspection/data_validation.json`
- `working/artifacts/review-remediation/01-data-tests.txt`

## 4. 数据结构改造

- [ ] **Step 1: 在 `data.py` 增加人工点结构**

新增 dataclass：

```python
@dataclass(frozen=True)
class ManualPoint:
    manual_point_id: str
    x_m: float
    y_m: float
    manual_service_time_s: float
    mapped_node_ids: tuple[int, ...]
```

修改 `ProblemData`：

```python
@dataclass(frozen=True)
class ProblemData:
    params: UAVParams
    targets: list[Target]
    manual_points: dict[str, ManualPoint]
    flight_time_s: dict[tuple[int, int], float]
    flight_energy_j: dict[tuple[int, int], float]
    ground_time_s: dict[tuple[str, str], float]
```

验收：现有调用 `data.targets`、`data.flight_time_s`、`data.ground_time_s` 的代码不需要改名，只新增 `data.manual_points`。

- [ ] **Step 2: 实现 `_read_manual_points`**

函数签名：

```python
def _read_manual_points(ws: Any) -> dict[str, ManualPoint]:
```

读取规则：

1. 从 `ManualPoints` 表读取 `manual_point_id`、坐标、服务时间和映射目标。
2. 人工点编号必须包含 `MP01` 到 `MP16`，允许按实际表头顺序读取，不依赖硬编码列号之外的表头含义。
3. `manual_service_time_s` 必须大于 0。
4. `mapped_node_ids` 必须指向 `NodeData` 中存在的目标。

失败示例：

```python
raise ValueError("ManualPoints validation failed: MP08 has non-positive service time")
```

- [ ] **Step 3: 在 `load_problem_data` 中读取 `ManualPoints`**

改成：

```python
manual_points = _read_manual_points(wb["ManualPoints"])
return ProblemData(
    params=params,
    targets=targets,
    manual_points=manual_points,
    flight_time_s=flight_time_s,
    flight_energy_j=flight_energy_j,
    ground_time_s=ground_time_s,
)
```

验收：`load_problem_data("2026同济数学建模竞赛赛题/2026C数据.xlsx")` 返回对象中 `len(data.manual_points) == 16`。

## 5. 一致性校验

- [ ] **Step 4: 增强 `validate_problem_data`**

返回字典必须新增字段：

```python
{
    "manual_point_count": 16,
    "manual_service_sum_from_manual_points_s": 2910.0,
    "manual_service_sum_from_node_data_s": 2670.0,
    "manual_service_time_conflicts": [
        {
            "manual_point_id": "MP02",
            "node_data_service_time_s": 180.0,
            "manual_points_service_time_s": 210.0
        }
    ],
    "flight_time_matrix_complete": True,
    "flight_energy_matrix_complete": True,
    "ground_time_matrix_complete": True,
    "matrix_diagonal_zero": True,
    "matrix_values_nonnegative": True,
    "priority_weight_values": [1, 2, 3],
    "checks_sheet_consistency": True
}
```

数值以实际 Excel 读取结果为准，字段名必须稳定。

- [ ] **Step 5: 校验无人机矩阵完整性**

检查 `FlightTime` 和 `FlightEnergy`：

```python
for i in range(0, 17):
    for j in range(0, 17):
        assert (i, j) in matrix
```

运行时不能使用 `assert`，需要显式抛出 `ValueError`：

```python
if (i, j) not in data.flight_time_s:
    raise ValueError(f"FlightTime matrix missing edge {(i, j)}")
```

- [ ] **Step 6: 校验地面矩阵完整性**

地面节点集合：

```python
ground_nodes = ("P0",) + tuple(sorted(data.manual_points))
```

检查所有 `(a, b)` 是否存在、是否非负、对角线是否为 0。

## 6. 求解器改造

- [ ] **Step 7: 修改 `solve_ground_tsp` 的服务时间来源**

当前逻辑从 `data.targets` 的第一条匹配目标推断服务时间。改为：

```python
service_by_point = {
    pid: mp.manual_service_time_s
    for pid, mp in data.manual_points.items()
}
```

缺失人工点必须报错：

```python
missing = [pid for pid in distinct_points if pid not in service_by_point]
if missing:
    raise ValueError(f"Manual service time missing for points: {missing}")
```

- [ ] **Step 8: 修改 `_direct_confirm_score` 的地面收益读取**

禁止：

```python
data.ground_time_s.get(("P0", mp), 0.0)
```

改成：

```python
ground_savings = (
    data.ground_time_s[("P0", mp)]
    + data.ground_time_s[(mp, "P0")]
    + data.manual_points[mp].manual_service_time_s
)
```

如果缺边，Python `KeyError` 会暴露问题；更友好的实现可先检查并抛出 `ValueError`。

## 7. 测试

- [ ] **Step 9: 新增数据冲突测试**

在 `tests/test_data.py` 增加：

```python
def test_manual_points_are_authoritative_for_service_time(problem_data):
    validation = validate_problem_data(problem_data)
    conflicts = validation["manual_service_time_conflicts"]
    assert conflicts
    assert any(c["manual_point_id"] == "MP02" for c in conflicts)
    assert validation["manual_service_sum_from_manual_points_s"] >= (
        validation["manual_service_sum_from_node_data_s"]
    )
```

- [ ] **Step 10: 新增矩阵完整性测试**

```python
def test_all_matrices_are_complete(problem_data):
    validation = validate_problem_data(problem_data)
    assert validation["flight_time_matrix_complete"] is True
    assert validation["flight_energy_matrix_complete"] is True
    assert validation["ground_time_matrix_complete"] is True
    assert validation["matrix_values_nonnegative"] is True
```

- [ ] **Step 11: 新增地面服务时间来源测试**

在 `tests/test_problem2.py` 增加：

```python
def test_ground_tsp_uses_manual_points_service_time(problem_data):
    result = solve_ground_tsp(problem_data, ("MP02",))
    assert result.service_time_s == problem_data.manual_points["MP02"].manual_service_time_s
```

## 8. 运行命令

```bash
.venv/bin/python -m pytest tests/test_data.py tests/test_problem2.py -q \
  | tee working/artifacts/review-remediation/01-data-tests.txt
```

重新生成数据验证：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from c_uav_inspection.data import load_problem_data, validate_problem_data
from c_uav_inspection.experiments import _write_json

data = load_problem_data(Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"))
_write_json(Path("outputs/c_uav_inspection/data_validation.json"), validate_problem_data(data))
PY
```

## 9. 验收标准

1. `data.manual_points` 存在且含 16 个点。
2. `solve_ground_tsp` 使用 `ManualPoints` 服务时间。
3. `data_validation.json` 明确列出 `MP02`, `MP08`, `MP09`, `MP13`, `MP16` 的服务时间冲突。
4. 任何矩阵缺边都会报错，不会被默认 0 替代。
5. 论文中的数据说明同步为“人工复核服务时间以 `ManualPoints` 为准”。
