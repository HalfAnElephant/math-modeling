# C题 SCI 级审查问题修复完整解决方案

本目录是 `PROBLEMS.md` 的唯一执行入口。原有 `IMPORVEMENT_PLAN` 主计划与 `subplans` 已被本方案替换，后续修复以这些步骤文件夹为准。

## 执行顺序

| 顺序 | 文件夹 | 主要目标 | 关键审查项 |
|---:|---|---|---|
| 00 | `00_总览与执行规则` | 建立全局规则、覆盖矩阵和执行纪律 | 全部 |
| 01 | `01_数据权威性与一致性修复` | 修复数据源冲突和矩阵校验缺口 | C-05, M-06, M-07, M-08 |
| 02 | `02_形式化模型与评价体系重构` | 补完整优化模型，重建推荐指标 | C-08, C-09, M-03, M-11 |
| 03 | `03_问题一时间优先与高优先级早完成` | 修复问题1求解口径与优先级早完成性 | C-10, C-11, M-01, M-02, M-04, M-05, M-09 |
| 04 | `04_问题二直接确认候选集与帕累托推荐` | 纳入全直接确认和帕累托推荐 | C-01, C-02, C-04, M-10 |
| 05 | `05_全枚举验证与搜索算法修复` | 修复全枚举排名并验证搜索质量 | C-03, C-07, M-12 |
| 06 | `06_实验体系重跑与结果文件治理` | 重跑实验、治理过期输出和敏感性解释 | C-12, M-13, W-08 |
| 07 | `07_论文硬错误修正与自动同步` | 修正论文事实错误，自动同步表格 | C-06, W-01, W-02, W-03, W-04, W-05, W-06, W-07, M-14, M-15, M-16, M-17 |
| 08 | `08_测试复现与最终验收` | 跑测试、构建 Word、形成交付清单 | M-18 与全部回归 |

## 全局命令

从项目根目录执行：

```bash
cd "/Users/xcy/Documents/100 项目/数学建模"
```

常规测试：

```bash
.venv/bin/python -m pytest tests/test_data.py tests/test_model.py tests/test_objective.py -q
.venv/bin/python -m pytest tests/test_problem1.py tests/test_problem1_time.py tests/test_search.py -q
.venv/bin/python -m pytest tests/test_problem2.py tests/test_exact.py -q
```

常规实验与图表：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments
from c_uav_inspection.plots import generate_all_figures

data_path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")
out = Path("outputs/c_uav_inspection")
run_all_experiments(data_path, out, include_expensive=False)
generate_all_figures(data_path, out)
PY
```

昂贵全枚举实验只在步骤 05 和最终验收时执行：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments

run_all_experiments(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
    include_expensive=True,
)
PY
```

Word 成稿生成：

```bash
.venv/bin/python build_paper.py
```

## 全局禁止事项

1. 禁止手工编辑原始 Excel。
2. 禁止手工编辑 `C题论文_多无人机联合巡检优化.docx`。
3. 禁止在论文里保留未由 CSV/JSON 支撑的推荐数值。
4. 禁止使用 `.get(..., 0.0)` 掩盖矩阵缺边或服务时间缺失。
5. 禁止把同一实验表内 min-max 归一化分数用于跨实验推荐。
6. 禁止把启发式结果写成全局最优，除非步骤 05 的全枚举或等价验证支持。

## 最终完成定义

所有步骤完成后，必须同时满足：

1. `outputs/c_uav_inspection/data_validation.json` 记录数据一致性结论。
2. `outputs/c_uav_inspection/problem2_exact_summary.json` 与 `problem2_exact_top.csv` 实际生成。
3. 论文删除“全部直接确认能耗不可行”等事实错误。
4. 推荐方案来自统一候选集、帕累托前沿或明确业务约束。
5. `report/c_uav_inspection_paper.md`、`report/c_uav_inspection_results.md` 与输出文件一致。
6. `C题论文_多无人机联合巡检优化.docx` 由脚本重新生成。
7. 测试记录写入 `working/artifacts/final-verification/`。
