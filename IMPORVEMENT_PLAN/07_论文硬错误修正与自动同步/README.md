# 论文硬错误修正与自动同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除论文中的事实错误和过强结论，建立从 CSV/JSON 自动同步表格与关键数字的流程，并重建 Word 成稿。

**Architecture:** `report/c_uav_inspection_paper.md` 是唯一论文源；新增结果同步脚本把实验输出转为 Markdown 表格片段；`build_paper.py` 只负责从 Markdown 生成 Word。所有人工改写围绕结果解释、模型假设和文献综述，不手工填数字。

**Tech Stack:** Python 3.11, Markdown, CSV/JSON, `build_paper.py`, optional Pandoc.

---

## 1. 覆盖问题

本步骤覆盖：

- C-02：删除“全部直接确认能耗不可行”。
- C-06：修正推荐方案地面时间拆分。
- C-08：补形式化模型。
- C-09：修正归一化解释。
- C-12：修正能量敏感性解释。
- M-14：补参考文献。
- M-15：降低创新点表述。
- M-16：修正复杂度分析。
- M-17：补复现入口。
- W-01 到 W-08：论文写作和数字表述问题。

## 2. 文件清单

修改：

- `report/c_uav_inspection_paper.md`
- `report/c_uav_inspection_results.md`
- `build_paper.py`
- 可新增：`report/sync_results.py`
- 可新增：`tests/test_report_sync.py`

输出：

- `report/generated_tables/`
- `C题论文_多无人机联合巡检优化.docx`
- `working/artifacts/review-remediation/07-build-paper.txt`

## 3. 论文硬错误清单

- [ ] **Step 1: 删除或替换事实错误句**

必须处理：

1. “全部直接确认（能耗不可行）”改为“全部直接确认可行但成本较高”，前提是输出文件确认可行。
2. “超出运营时长上限 2600 s 较多但仍在约束范围内”改为“低于运营时长上限，仍有余量”。
3. “`E_max` 降至 `121500 J` 时直接确认集不变”改为读取 CSV 后的真实集合变化。
4. “地面通行时间 1061 s、服务时间 1608 s”改为由 `recommended_solution.json` 和地面路径重算出的真实通行与服务拆分。

- [ ] **Step 2: 修正推荐方案表述**

推荐方案段落必须包含：

```text
推荐方案来自统一候选池和帕累托筛选。默认重建搜索仅作为候选生成器；若全直接确认、不可拆分悬停或高容忍度搜索在主要指标上更优，论文按预设推荐规则选择或解释不选择的业务原因。
```

## 4. 自动同步脚本

- [ ] **Step 3: 新增 `report/sync_results.py`**

脚本职责：

1. 读取 `outputs/c_uav_inspection/MANIFEST.md` 确认可用输出。
2. 读取核心 CSV/JSON。
3. 生成 Markdown 表格到 `report/generated_tables/`。
4. 生成 `report/generated_tables/key_numbers.json`，集中保存摘要数字。

建议函数：

```python
def load_outputs(output_dir: Path) -> dict[str, Any]:
    files = {
        "manifest": output_dir / "MANIFEST.md",
        "recommended": output_dir / "recommended_solution.json",
        "candidate_pool": output_dir / "problem2_candidate_pool.csv",
        "pareto_front": output_dir / "problem2_pareto_front.csv",
        "exact_summary": output_dir / "problem2_exact_summary.json",
    }
    missing = [str(path) for path in files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required output files: {missing}")
    return files

def render_problem2_candidate_table(rows: list[dict[str, Any]]) -> str:
    header = "| 候选 | 闭环时间/s | 人工点数 | 加权人工代价 | 总能耗/J |\n|---|---:|---:|---:|---:|"
    body = [
        f"| {row['candidate_id']} | {float(row['closed_loop_time_s']):.2f} | "
        f"{row['manual_count']} | {row['weighted_manual_cost']} | "
        f"{float(row['total_energy_j']):.0f} |"
        for row in rows
        if row.get("feasible") in ("True", True)
    ]
    return "\n".join([header, *body])

def render_recommended_solution_summary(data: dict[str, Any]) -> str:
    return (
        f"推荐候选 `{data['candidate_id']}`，选择规则为 "
        f"`{data['selection_rule']}`，闭环时间 "
        f"{float(data['closed_loop_time_s']):.2f} s。"
    )

def main() -> None:
    output_dir = Path("outputs/c_uav_inspection")
    generated_dir = Path("report/generated_tables")
    generated_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 在论文中使用同步片段**

采用稳定标记：

```markdown
<!-- BEGIN:problem2_candidate_table -->
自动生成表格内容
<!-- END:problem2_candidate_table -->
```

`sync_results.py` 替换标记区间内容。禁止手工改标记区间内的数字。

## 5. 模型与复杂度章节

- [ ] **Step 5: 补完整模型章节**

插入步骤 02 中定义的变量和约束。若本文不求解完整 MILP，必须写清：

```text
由于完整模型包含多旅行商、多趟能耗约束、可拆分悬停和空地协同决策，本文采用形式化约束定义问题，并使用可复现启发式与全枚举候选验证求解小规模实例。
```

- [ ] **Step 6: 修正复杂度分析**

复杂度表：

| 模块 | 复杂度口径 |
|---|---|
| 最近邻 | `O(n^2)` |
| 2-opt | 单航次约 `O(m^3)` 或按实现说明 |
| 可拆分悬停装箱 | `O(Rn)`，不是简单 `O(n)` |
| 地面 Held-Karp | `O(|M|^2 2^{|M|})` |
| 问题1子集 DP | `O(K 3^n)` 量级或按实际子集枚举说明 |
| 直接确认全枚举 | `O(2^n * rebuild_cost)` |

## 6. 文献与创新表述

- [ ] **Step 7: 扩充参考文献方向**

至少覆盖：

1. Energy-constrained UAV routing。
2. Multi-trip vehicle routing。
3. Split-delivery 或 split-service routing。
4. UAV-ground cooperative inspection。
5. Ruin-and-recreate 或 metaheuristics。
6. Multi-objective optimization and Pareto decision。

引用格式统一，包含作者、年份、题名、期刊或会议、卷期页码或 DOI。没有 DOI 的文献也要保持格式一致。

- [ ] **Step 8: 降低创新点表述**

将“原创提出”类表述改为：

```text
本文将可拆分服务、能耗约束多趟路径、空地闭环复核和帕累托候选评价组合到智慧社区巡检场景中，形成可解释、可复现的建模求解流程。
```

## 7. 测试与构建

- [ ] **Step 9: 测试同步脚本**

```python
def test_sync_results_generates_key_numbers(tmp_path):
    # 使用真实 outputs 目录或测试夹具
    main()
    assert Path("report/generated_tables/key_numbers.json").exists()
```

- [ ] **Step 10: 运行同步和构建**

```bash
.venv/bin/python report/sync_results.py \
  | tee working/artifacts/review-remediation/07-sync-results.txt

.venv/bin/python build_paper.py \
  | tee working/artifacts/review-remediation/07-build-paper.txt
```

## 8. 验收标准

1. `report/c_uav_inspection_paper.md` 不再包含 `能耗不可行` 这类错误断言。
2. 论文中推荐方案数字可在输出 CSV/JSON 中找到来源。
3. 地面时间拆分由代码或输出文件同步，通行时间与服务时间相加等于总地面时间。
4. 参考文献数量和主题覆盖足以支撑方法定位。
5. `C题论文_多无人机联合巡检优化.docx` 由 `build_paper.py` 重新生成。
