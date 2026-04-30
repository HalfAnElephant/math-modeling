# C题：面向智慧社区的多无人机-物业人员联合巡检优化结果说明

## 1. 数据与约束核验

数据来源于2026年同济数学建模竞赛C题Excel工作簿。数据核验结果如下：

- 目标点数量：16个，全部数据完整。
- 基础悬停总时间：**790 s**（所有目标仅接受基础巡检所需累计悬停）。
- 全部直接确认悬停总时间：**5210 s**（所有目标达到直接确认阈值所需累计悬停）。
- 直接确认阈值有效性：全部16个目标的 `direct_confirm_time_s` 均不小于 `base_hover_time_s`，合规。
- 单趟有效能耗上限：**135000 J**（`effective_energy_limit_J`）。
- 单目标最大直接确认往返能耗：132986 J，在单趟能耗上限以内。

## 2. 问题1模型说明

问题1要求仅使用无人机对所有目标进行基本巡检，每个目标接受不少于其 `base_hover_time_s` 的悬停时间。

求解方法（两种方案）：
**方案A — 沿序列切分装箱（packed）：**
- 以最近邻贪心策略生成目标访问顺序（从服务中心0出发，每次选飞行时间最短的未访问目标）。
- 采用可拆分悬停装箱算法（divisible hover bin-packing）将访问顺序切分为满足单趟能耗约束的无人机趟次。单个目标的悬停需求可跨趟次拆分。
- 对每条路线应用2-opt局部搜索，在不改变目标集合和悬停分配的前提下优化访问顺序。
- 按最长处理时间优先（LPT）策略将趟次分配给K架无人机，以均衡负载。

**方案B — 时间优先子集分配（time-priority DP）：**
- 枚举全部非空目标子集，对每个子集独立构造能量可行路线（最近邻+2-opt）。
- 通过动态规划将完整目标集划分为至多K个子集，使最长路线时长最小化。
- 每架无人机仅执行1趟任务，充分发挥多无人机的并行优势。

两种方案的对比表明：packed方案在K≥2后性能锁定（受固定序列约束），而time-priority方案在K≥2后阶段时间持续下降，验证了通过目标子集并行分配可突破结构限制。

多目标评估采用归一化加权：所有指标在加权求和前先逐项 min-max 归一化到 [0, 1] 区间。归一化权重为：无人机阶段时间权重 1.0，总能耗权重 0.0，负载标准差权重 0.0（侧重时间效率）。`normalized_objective` 只用于同一实验表内比较。

## 问题1时间优先复核

本轮修订新增时间优先划分验证，避免将“少航次满载装箱”误写为“时间最优”。结果文件为 `problem1_time_priority_k_comparison.csv` 和 `problem1_parallel_route_count_ablation.csv`。当前结果显示，time-priority DP在 $K=4$ 时将基础巡检阶段时间降至 **268.90 s**，优于packed基准在 $K=2,3,4$ 下锁定的 **639.33 s**；因此问题1的时间优先推荐配置为 $K=4$。

## 3. 问题2模型说明

问题2引入物业人员地面复核，形成闭环巡检。目标接受无人机悬停巡检后，若累计悬停时间达到有效直接确认阈值，则直接确认；否则需物业人员前往该目标的物业人工点进行地面复核。

有效直接确认阈值为 **max(base_hover_time_s, direct_confirm_time_s * multiplier)**，保证阈值不低于基础悬停时间。

物业人员在**全部无人机任务完成后**出发，沿最优TSP路径（Held-Karp精确算法）依次访问所需人工点，完成全部地面复核。

闭环时间 = 无人机阶段时间（T_u）+ 地面复核时间（T_g）。

求解方法（重建搜索，rebuild search）：
- 从空直接确认集（全部目标仅基悬停）出发，计算基线闭环性能。
- 对每个目标计算直接确认获益/代价评分（综合考虑额外悬停成本、地面节省、能耗代价）。
- 按评分从高到低逐一尝试将目标加入直接确认集，每次触发完整的路线重建（ruin-and-recreate）。
- 接受条件：闭环时间严格减少，或人工点数减少且闭环时间不超过当前最优的1.03倍。
- 相较贪心单点修改，重建搜索具有更强的全局搜索能力。

问题2的归一化权重使用：

| 指标 | 权重 | 说明 |
|------|------|------|
| closed_loop_time_s | 0.45 | 闭环总时间，权重最高 |
| ground_review_time_s | 0.20 | 地面复核时间 |
| weighted_manual_cost | 0.15 | 优先级加权人工复核代价 $C_M=\sum_{i\in M}p_i$ |
| manual_count | 0.10 | 人工复核点数量 |
| total_energy_j | 0.05 | 总能耗 |
| load_std_s | 0.05 | 多无人机负载标准差 |

权重设计说明：闭环时间作为核心效率指标占主导；加权人工复核代价 $C_M$ 纳入目标优先级权重 $p_i$，使高优先级目标的复核义务得到体现；其余指标作为辅助解释维度。

## 问题2优先级权重

问题2已将 `priority_weight` 纳入加权人工复核代价 $C_M$、重建搜索评分和归一化目标函数。推荐方案在 $K=4,\alpha=1.00$ 下直接确认7个目标，人工复核9个目标，$C_M=21$；相比仅基础巡检的16个人工复核目标和 $C_M=36$，物业端复核压力明显降低。

## 4. 算法说明

主要算法组件：

1. **最近邻路径构造（Nearest Neighbor）**：$O(n^2)$ 贪婪算法，从服务中心0出发，每次选择飞行时间最短的未访问目标，用于生成初始访问顺序。

2. **2-opt局部搜索**：对每条无人机趟次路线做2-opt边交换优化，保证能耗可行性前提下减少飞行时间。单条航线复杂度 $O(m^3)$，$m$ 为航线目标数。

3. **可拆分悬停装箱**：沿访问顺序依次填充单趟能耗预算，当某目标悬停需求超出剩余能耗时，部分服务后结束当前趟次，剩余需求由后续趟次接力完成。复杂度 $O(n)$。

4. **LPT负载均衡**：将趟次按悬停总时长降序排列，依次分配给当前累计工作量最小的无人机，配合换电时间计入，均衡多无人机负载。

5. **Held-Karp精确TSP**：$O(|M|^2 \cdot 2^{|M|})$ 动态规划求解地面人员最优访问路径，适用于小规模人工点集合（通常不超过16个）。

6. **重建搜索（Rebuild Search）**：每次候选评价触发完整路线重规划，外层遍历16个候选目标，每次接受后更新直接确认集合并重建全部航次。最坏情况下触发16次重建，单次重建包含装箱、2-opt、LPT和TSP。

7. **时间优先子集分配（Time-Priority DP）**：枚举全部目标子集独立构造能量可行路线，再通过动态规划划分为至多K个子集使最长路线最小化。用于问题1的方案B验证。

## 5. 输出文件

实验结果和图表输出至 `outputs/c_uav_inspection/`：

| 文件名 | 说明 |
|--------|------|
| `data_validation.json` | 数据核验摘要 |
| `problem1_k_comparison_current_packed.csv` | 问题1 packed方案 K=1..4 对比 |
| `problem1_time_priority_k_comparison.csv` | 问题1 time-priority DP方案 K=1..4 对比 |
| `problem1_parallel_route_count_ablation.csv` | 问题1 并行航次数消融实验 |
| `problem1_swap_sensitivity_k1.csv` | 问题1 K=1换电时间敏感性（换电进入关键路径） |
| `problem1_swap_sensitivity_k4_reference.csv` | 问题1 K=4换电时间参考（换电不进入关键路径） |
| `problem2_baseline_comparison.csv` | 仅基础巡检与联合优化闭环对比 |
| `problem2_k_comparison.csv` | 问题2 K=1..4 对比 |
| `problem2_threshold_sensitivity.csv` | 问题2阈值倍率敏感性 |
| `problem2_split_hover_ablation.csv` | 可拆分/不可拆分悬停消融对照 |
| `problem2_acceptance_tolerance_sensitivity.csv` | 重建搜索接受准则容忍倍率敏感性 |
| `problem2_energy_limit_sensitivity.csv` | 有效能量上限敏感性 |
| `problem2_hover_power_sensitivity.csv` | 悬停功率敏感性 |
| `recommended_solution.json` | 推荐方案（K=K_max, multiplier=1.0） |
| `problem1_k_comparison.png` | 问题1 packed 与 time-priority 对比图 |
| `problem2_baseline_comparison.png` | 仅基础巡检与联合优化对比图 |
| `problem2_k_comparison.png` | 问题2 K值对闭环时间与人工负担影响图 |
| `recommended_routes.png` | 推荐方案无人机+地面路径图 |
| `problem2_threshold_sensitivity.png` | 问题2阈值敏感性折线图 |
| `problem2_acceptance_tolerance_sensitivity.png` | 重建搜索接受准则敏感性图 |
| `problem2_energy_parameter_sensitivity.png` | 有效能量上限与悬停功率敏感性图 |
| `problem2_split_hover_ablation.png` | 可拆分/不可拆分悬停对照图 |

可选昂贵输出：

| 文件名 | 说明 |
|--------|------|
| `problem2_exact_summary.json` | `include_expensive=True` 时生成，记录直接确认集合全枚举摘要 |
| `problem2_exact_top.csv` | `include_expensive=True` 时生成，记录全枚举Top方案 |

全枚举默认不在 `run_all_experiments(..., include_expensive=False)` 中生成。当前64子集抽样评估耗时约7.53 s，完整65536子集枚举估算约128.5 min，适合作为赛后或最终复核开关，而不适合作为常规实验步骤。

推荐方案要点：
- 7个目标被无人机直接确认（node_id: 1, 4, 6, 7, 10, 12, 16）。
- 9个物业人工点需要地面复核（MP02, MP03, MP05, MP08, MP09, MP11, MP13, MP14, MP15）。
- 加权人工复核代价 $C_M=21$。
- 地面路径：P0 -> MP13 -> MP14 -> MP15 -> MP02 -> MP03 -> MP05 -> MP08 -> MP09 -> MP11 -> P0。
- 闭环总时间约 3303 s。

## 6. 论文写作建议

1. **强调归一化的必要性**：多目标各分量量纲不同（秒、焦耳、个数），直接加权会导致量纲大的项主导。务必在正文中说明"多目标加权前先归一化"。

2. **突出可拆分悬停机制**：悬停时间可跨无人机、跨趟次拆分是模型的核心创新点之一，使能耗约束下的巡检计划更加灵活紧凑。

3. **重建搜索 vs 贪心对比**：可在论文中讨论重建搜索相较于贪心单点修改的优势——每次候选评价触发完整路线重规划，避免了贪心方法的局部最优陷阱。

4. **有效直接确认阈值的合理性**：阈值取 `max(base_hover, direct_confirm * multiplier)` 保证了无人机至少完成基础巡检才能直接确认，符合实际巡检逻辑。

5. **闭环时间分解**：建议以图示分别呈现无人机阶段时间、地面复核时间、闭环总时间，直观展示两者关系。

6. **敏感性分析**：K值对比和阈值倍率敏感性分析为论文的参数讨论提供了充分的实验依据，建议以图表形式纳入正文或附录。
