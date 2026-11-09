# GateANN 选择率自适应的分层搜索前沿

## 1. 问题

原 GateANN 把满足过滤条件的“结果候选”和不满足条件的“隧道节点”放入同一个、容量为 `L` 的距离有序候选池。Low workload 的选择率中位数只有 0.545%，因此 `L=320` 时平均 `FilterSkips=320.69`，几乎全部预算被隧道节点占用，Recall@10 只有 34.3%。原版需要把 `L` 放大到 2560 才恢复到 83.75%，隧道跳过数同步增至 2538.51。

## 2. 设计

实现“工作保持（work-conserving）的软保留前沿”：

1. 加载过滤元数据时统计每个标签的频率；单标签查询得到精确选择率，多标签查询用最稀有标签频率作为子集选择率上界。
2. 仅当估计选择率低于阈值 `τ=1.5%` 时启用优化，Medium 与 High 自动执行原算法。
3. 在总候选池容量仍为 `L` 的前提下，为有效候选计算软保留比例：

   `r(s)=r_max·max(0, 1-s/τ)`，其中 `r_max=15%`。

4. 有效候选不足时，隧道节点可以借用全部空位；发现有效候选后，它可以回收被借用的槽位。已经保留的有效候选不会再被更近但无效的隧道候选挤出。
5. 候选仍按原 PQ 距离排序，I/O 前过滤、FullAdj 隧道和索引格式均不变；无需重建索引。

这不是扩大 `L`：优化前后的物理候选池上限相同。新增 `Promotions` 与 `Protections` 统计分别记录有效候选回收槽位和软保留受到保护的次数。

## 3. 文件

- `gateann_filter_frontier.patch`：相对 GateANN 固定提交 `71e87cb...` 的算法补丁，不包含课程已有的 AIO 兼容补丁。
- `run_comparison.sh`：三轮、交替执行顺序的 baseline/optimized A/B。
- `analyze.py`：生成逐轮结果与三轮中位数。
- `results/all_runs.csv`：全部原始归一化结果。
- `results/summary.csv`：按 variant/bucket/L 聚合的中位数和范围。

实验工作树为 `systems/GateANN-filter-frontier`；未修改的对照工作树仍为 `systems/GateANN-public`。

## 4. 应用与编译

```bash
bash scripts/prepare_gateann.sh
git -C systems/GateANN-public apply \
  ../../optimization/filter_frontier/gateann_filter_frontier.patch
cmake --build systems/GateANN-public/build \
  --target search_disk_index_yfcc -j 8
```

运行最终三轮实验：

```bash
bash optimization/filter_frontier/run_comparison.sh \
  "$PWD/systems/GateANN-public" "$PWD/course_runs" frontier-final-v2 3
```

适配器通过 `--frontier-max-reserve` 与 `--frontier-selectivity-threshold` 记录参数；传入 `0` 可在同一二进制中精确关闭策略。

## 5. 三轮正式结果

所有数字均为三轮中位数，Formal 1M、threads=1、beamwidth=8、K=10、FullAdj=32。

| 方案 | Bucket | L | Recall@10 | 延迟 (µs) | QPS | Mean I/O | FilterSkips |
|---|---|---:|---:|---:|---:|---:|---:|
| Baseline | Low | 320 | 34.30% | 883.4 | 1132 | 4.38 | 320.69 |
| Optimized | Low | 320 | 81.30% | 1776.2 | 563 | 23.55 | 300.28 |
| Baseline | Low | 2560 | 83.75% | 5988.0 | 167 | 25.06 | 2538.51 |
| Optimized | Low | 360 | 83.65% | 1926.8 | 519 | 26.03 | 337.75 |
| Baseline | Low | 2560 | 83.75% | 5988.0 | 167 | 25.06 | 2538.51 |
| Optimized | Low | 400 | 85.25% | 2232.1 | 448 | 28.31 | 375.30 |

在近似等召回点（83.75% vs 83.65%），优化把 `L` 从 2560 降到 360（-85.9%），延迟降低 67.8%，QPS 提高到 3.11×，FilterSkips 降低 86.7%；Mean I/O 从 25.06 增至 26.03（+3.9%）。若要求 Recall 不低于基线，优化 L=400 的 Recall 高 1.50 个百分点，延迟仍低 62.7%，QPS 为 2.68×。

Medium/High 均高于 1.5% 阈值，三轮中 `Promotions=Protections=0`，算法行为自动退化为原前沿。Medium L=320 的 Recall/I/O/FilterSkips 完全一致（72.05%/16.75/309.25），延迟中位数 1003.0 vs 1011.1 µs；High L=320 的 Recall 和 I/O 均为 93.2%/46.74。绝对延迟受同机负载波动影响，因此回归判断以策略计数、Recall、I/O 和三轮范围共同作证，不把 High 的偶然加速归因于本优化。

## 6. 代价与边界

Low 的同一 `L` 延迟会上升，因为更多真正有效的节点被保留并触发 SSD I/O；正确比较应使用等召回点。新增标签频率数组需要 `4×标签数` 字节，课程数据约 0.8 MiB。多标签查询的选择率估计是上界，可能保守地关闭优化；参数 `τ` 与 `r_max` 仍应在不同数据分布上验证。
