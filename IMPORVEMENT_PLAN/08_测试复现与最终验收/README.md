# 测试复现与最终验收 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对全部修复进行可复现验收，解决慢测试和不稳定测试问题，形成最终交付证据。

**Architecture:** 测试分层运行，慢测试显式标记，昂贵全枚举单独执行并记录耗时。最终验收以文件清单、测试记录、实验 manifest 和论文构建日志为证据。

**Tech Stack:** `pytest`, shell commands, CSV/JSON inspection, `build_paper.py`.

---

## 1. 覆盖问题

- M-18：测试套件过慢，且全量测试未稳定完成。
- 全部 C/M/W 审查项的最终回归。

## 2. 文件清单

修改：

- `pytest.ini` 或 `pyproject.toml`
- `tests/test_experiments.py`
- `tests/test_exact.py`
- `tests/test_blackbox*.py`
- `report/c_uav_inspection_results.md`

输出：

- `working/artifacts/final-verification/test-fast.txt`
- `working/artifacts/final-verification/test-slow.txt`
- `working/artifacts/final-verification/experiment-run.txt`
- `working/artifacts/final-verification/exact-run.txt`
- `working/artifacts/final-verification/build-paper.txt`
- `working/artifacts/final-verification/file-inventory.txt`
- `working/artifacts/final-verification/final-checklist.md`

## 3. 测试分层

- [ ] **Step 1: 标记慢测试**

在 `pytest.ini` 或 `pyproject.toml` 中增加：

```ini
[pytest]
markers =
    slow: tests that run full experiments or expensive enumeration
    expensive: tests that enumerate all direct-confirm subsets
```

将全枚举测试标记：

```python
@pytest.mark.expensive
def test_expensive_experiment_writes_exact_files(tmp_path, data_path):
    run_all_experiments(data_path, tmp_path, include_expensive=True)
    assert (tmp_path / "problem2_exact_summary.json").exists()
    assert (tmp_path / "problem2_exact_top.csv").exists()
```

将完整实验重跑测试标记：

```python
@pytest.mark.slow
def test_run_all_experiments_outputs_all_files(tmp_path, data_path):
    run_all_experiments(data_path, tmp_path, include_expensive=False)
    assert (tmp_path / "MANIFEST.md").exists()
    assert (tmp_path / "recommended_solution.json").exists()
```

- [ ] **Step 2: 快速测试不运行昂贵枚举**

快速测试命令：

```bash
.venv/bin/python -m pytest tests -q -m "not slow and not expensive"
```

预期：不触发 65536 子集枚举，不超过合理时间。若仍超过 5 分钟，继续拆分慢测试。

- [ ] **Step 3: 慢测试单独运行**

```bash
.venv/bin/python -m pytest tests -q -m "slow and not expensive"
```

- [ ] **Step 4: 昂贵测试单独运行**

```bash
.venv/bin/python -m pytest tests -q -m "expensive"
```

## 4. 最终复现流程

- [ ] **Step 5: 创建验收目录**

```bash
mkdir -p working/artifacts/final-verification
```

- [ ] **Step 6: 快速测试**

```bash
.venv/bin/python -m pytest tests -q -m "not slow and not expensive" \
  | tee working/artifacts/final-verification/test-fast.txt
```

- [ ] **Step 7: 慢测试**

```bash
.venv/bin/python -m pytest tests -q -m "slow and not expensive" \
  | tee working/artifacts/final-verification/test-slow.txt
```

- [ ] **Step 8: 常规实验与图表**

```bash
.venv/bin/python - <<'PY' 2>&1 | tee working/artifacts/final-verification/experiment-run.txt
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments
from c_uav_inspection.plots import generate_all_figures

data_path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")
out = Path("outputs/c_uav_inspection")
run_all_experiments(data_path, out, include_expensive=False)
generate_all_figures(data_path, out)
PY
```

- [ ] **Step 9: 全枚举实验**

```bash
/usr/bin/time -p .venv/bin/python - <<'PY' 2>&1 | tee working/artifacts/final-verification/exact-run.txt
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments

run_all_experiments(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
    include_expensive=True,
)
PY
```

- [ ] **Step 10: 论文同步与 Word 构建**

```bash
.venv/bin/python report/sync_results.py \
  | tee working/artifacts/final-verification/sync-results.txt

.venv/bin/python build_paper.py \
  | tee working/artifacts/final-verification/build-paper.txt
```

- [ ] **Step 11: 文件清单**

```bash
find outputs/c_uav_inspection report working/artifacts/final-verification \
  -maxdepth 2 -type f | sort \
  > working/artifacts/final-verification/file-inventory.txt
```

## 5. 最终清单

- [ ] **Step 12: 编写 `final-checklist.md`**

内容模板：

````markdown
# Final Verification Checklist

## Tests
- Fast tests: passed, see test-fast.txt
- Slow tests: passed, see test-slow.txt
- Expensive enumeration: passed, see exact-run.txt

## Data
- ManualPoints authority documented
- Service time conflicts listed in data_validation.json
- Matrix completeness checks passed

## Problem 1
- Time-priority and packed candidates generated
- Priority completion metrics generated
- Marginal benefit table generated

## Problem 2
- Candidate pool generated
- Pareto front generated
- All-direct baseline represented
- Exact enumeration represented
- Recommended solution has selection rule

## Paper
- Hard factual errors removed
- Tables synced from outputs
- Word rebuilt from Markdown
````

所有条目后附对应文件路径。

## 6. 验收标准

1. 快速测试、慢测试、昂贵测试均有日志。
2. `problem2_exact_summary.json` 在最终输出中存在。
3. `MANIFEST.md` 与 `file-inventory.txt` 一致。
4. `recommended_solution.json` 包含 `selection_rule` 和 `recommendation_reason`。
5. 论文 Markdown 与 Word 均为最新构建结果。
6. `final-checklist.md` 明确列出每个审查大类的完成证据。
