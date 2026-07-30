# 果蝇 VR 数据预处理与分析流程

更新日期：2026-07-15

本文档给出从单次实验检查、逐帧数据清洗到组间统计的推荐流程。它只描述当前分享包能够直接产生和处理的数据，不假定存在额外的 `tools` 分析脚本。

## 1. 分析目标和数据单位

当前实验包含 18 个视觉状态：

- 3 种背景颜色
- 3 个亮度等级
- 无刺激和有刺激两个区块

每个状态默认 20 秒，一次完整实验默认约 360 秒。

建议区分三个分析层级：

| 层级 | 一行代表什么 | 适合用途 |
| --- | --- | --- |
| 帧级 | 一个 FicTrac 有效采样 | 轨迹、速度时间序列、朝向和接近判定 |
| 状态级 | 一只果蝇在一个视觉状态下的汇总 | 主要统计分析 |
| 个体级 | 一只果蝇整场实验的汇总 | 样本质控和总体活动水平 |

统计推断时，生物学重复单位是果蝇，不是帧。不能把同一只果蝇的数万帧当作数万个独立样本。

## 2. 每次实验的文件

推荐每只果蝇、每次实验使用独立目录：

```text
exp_data/
├─ wing_01_1/
│  ├─ experiment_settings.json
│  ├─ fictrac_config.txt
│  ├─ fictrac-*.dat
│  ├─ fictrac-*.log
│  ├─ drosophila_exp_*.csv
│  └─ drosophila_exp_*_phase_summary.csv
└─ no_wing_01_1/
   └─ ...
```

文件名中的 `phase_summary` 是旧版兼容命名，当前实际是 18 个状态的汇总。

分析时保留：

- 原始 `.dat` 和 `.log`
- 主 CSV
- 独立状态汇总 CSV
- `experiment_settings.json`
- 本次实验的 `fictrac_config.txt`

不要只保留图片而删除原始数据。

## 3. 读取主 CSV

主 CSV 包含两个区域：

1. 文件开头的逐帧表
2. 两个空行后的 `=== State Summary ===`

逐帧分析只读取标记之前的部分。当前三个画图脚本已经在遇到空行、`=== Phase Summary ===` 或 `=== State Summary ===` 时停止读取。

如果使用自己的 pandas 脚本，也应先截取逐帧区域，避免把状态汇总行误当作帧数据。

## 4. 第一轮完整性检查

每个实验先检查以下内容。

### 4.1 文件和配置

- 主 CSV 存在且可以读取。
- 独立 `*_phase_summary.csv` 存在。
- `experiment_settings.json` 存在。
- CSV 包含 `Cfg_*` 配置列。
- `Cfg_SIMULATION_MODE` 在正式实验中为 false。
- `Cfg_SPHERE_RADIUS_CM`、屏幕 FOV 和亮度参数符合本次实验记录。

### 4.2 状态完整性

- `State_Index` 应覆盖 1-18。
- 每个状态应有有效帧。
- 每个状态持续时间应接近 `Cfg_STATE_DURATION_S`。
- 前 9 个状态应为 `no_stimulus`。
- 后 9 个状态应为 `stimulus`。
- 每个区块内应包含 3 背景 × 3 亮度的 9 个组合。

状态顺序是随机的。跨实验匹配条件时使用：

```text
State_Block
State_BG_Name
State_Brightness_Label
State_Stimulus_On
```

不要假设不同果蝇的 `State_Index=4` 是同一视觉条件。

### 4.3 时间完整性

检查：

- `Time_s` 单调递增。
- `FT_Timestamp_ms` 大体递增。
- `FT_Delta_ms` 大多数接近实际相机帧间隔。
- `FT_Seq` 通常递增。
- 没有长时间无数据区间。

180 FPS 时理论帧间隔约为：

```text
1000 / 180 = 5.556 ms
```

当前状态汇总中的 `DroppedFrame_Estimate` 把 `FT_Delta_ms > 10 ms` 左右的间隔记为一次可疑长间隔。它是快速质控指标，不是精确丢帧数量。

### 4.4 运动量合理性

检查以下列是否存在大跳变或长时间常数：

- `FT_Forward_cm`
- `FT_Lateral_cm`
- `Exp_Heading_rad`
- `Step_Distance_cm`
- `Exp_Speed_cm_s`
- `Exp_AngVel_rad_s`
- `VR_Fly_X_cm`
- `VR_Fly_Y_cm`

同时检查 FicTrac 日志中是否出现频繁跟踪失败、重定位或相机掉帧。

## 5. 时间和运动重建原则

### 5.1 正式实验起点

相机可以提前打开。只有在 VR 窗口按空格或单击鼠标后，程序才开始正式实验。

`Time_s` 已按这个原则记录，不需要再减去相机预热时间。空格后的第一个 FicTrac 包只用于建立基线，没有写入逐帧表。

### 5.2 时间基准

行为分析默认使用 `Time_s`。需要与 FicTrac 原始数据或视频对齐时，同时保留：

- `FT_Frame`
- `FT_Timestamp_ms`
- `FT_Seq`
- `FT_Delta_ms`

不要用 CSV 行号除以 180 代替真实时间，因为 UDP 抖动、丢帧和跟踪重置会破坏固定行号时间假设。

### 5.3 距离和轨迹

主要行为距离使用：

- 帧级步长：`Step_Distance_cm`
- 状态总身体运动距离：`Total_Distance_cm`
- VR 世界路径长度：`VR_Total_Distance_cm`
- VR 净位移：`VR_Net_Displacement_cm`

当前 `VR_ForwardGain=1.0`。不要再把 `VR_Fly_X_cm`、`VR_Fly_Y_cm` 或总距离除以 2，也不要做旧版增益补偿。

## 6. 保守的预处理顺序

所有处理都应保留原始列，新增处理后列，不能覆盖原始 CSV。

推荐顺序：

1. 截取逐帧区域。
2. 将关键列转为数值类型。
3. 按 `State_Index` 分段。
4. 检查 `Time_s`、`FT_Delta_ms` 和 `FT_Seq`。
5. 标记明显跟踪异常帧。
6. 在每个状态内部单独平滑，不跨状态边界。
7. 根据分析目的决定是否重新计算活动状态。
8. 生成状态级长表。

### 6.1 缺失值

- `Exp_MoveDir_rad` 在没有位移时为空，属于正常情况。
- 刺激锚点和条纹世界坐标在无刺激状态为空，属于正常情况。
- `Stim_Facing_Any` 和 `Stim_Approaching_Any` 在无刺激状态为 0。
- 其他关键运动列大面积缺失时，应回查 FicTrac 原始文件和日志。

### 6.2 异常值

不要仅凭一个统一阈值直接删除所有高速帧。建议结合：

- 静止球基线
- 速度和角速度分布
- FicTrac error score
- 前后帧轨迹连续性
- 视频人工抽查

建立异常标记列，例如 `QC_TrackingJump`，并在分析时报告过滤规则。

### 6.3 平滑

画图可使用短窗口滚动均值或中位数。当前行为时间线对速度和绝对角速度使用 15 帧居中滚动均值。

统计时建议同时保留：

- 原始速度
- 平滑速度
- 是否通过质控

平滑窗口不能跨越状态边界，否则会把相邻颜色或亮度条件混合。

### 6.4 活动状态

程序原始判定：

```text
Is_Moving =
    Exp_Speed_cm_s > Cfg_MOVEMENT_SPEED_THRESHOLD
    OR abs(Exp_AngVel_rad_s) > Cfg_MOVEMENT_ANG_VEL_THRESHOLD
```

如果后续根据静止噪声重新设置阈值，应新增 `Is_Moving_Clean`，并保留原始 `Is_Moving`。

## 7. 刺激相关变量

优先直接使用程序逐帧写入的：

- `Stim_Facing_Any`
- `Stim_Approaching_Any`
- `Stim_VisualHalfWidth_rad`
- `Stim_Mapped_Angle_rad`

原因是程序在每一帧已经知道果蝇位置、heading、运动方向、条纹世界坐标和动态渲染角宽。后期只用固定 30° 阈值重新计算，会丢失条纹随距离变化的真实视觉宽度。

解释：

- `Stim_Facing_Any=1`：果蝇 heading 落入前方或后方任一条纹的当前视觉半宽。
- `Stim_Approaching_Any=1`：果蝇达到前进速度阈值，且 VR 世界运动方向落入任一条纹视觉半宽。
- `Stim_VisualHalfWidth_rad`：最近条纹当前完整角宽的一半。

`Stim_Facing_Any` 表示看向刺激，`Stim_Approaching_Any` 表示运动方向朝向刺激，两者不是同一个行为。

## 8. 推荐的状态级主表

推荐建立长表，每一行代表“一只果蝇 × 一个状态”。

### 8.1 标识列

```text
wing_condition
fly_id
experiment_id
State_Block
State_BG_Name
State_Brightness_Label
State_Stimulus_On
State_Index
```

`State_Index` 只用于回到原始时间顺序，不作为跨实验条件主键。

### 8.2 质控列

```text
Duration_s
Total_Frames
Valid_Time_s
Mean_FT_Delta_ms
FT_Delta_SD_ms
DroppedFrame_Estimate
Tracking_Reset_Count
valid_state
```

### 8.3 主要行为指标

```text
Moving_Ratio_pct
Mean_MovingSpeed_cm_s
Total_Distance_cm
VR_Total_Distance_cm
VR_Net_Displacement_cm
VR_Path_Straightness
Mean_AngVel_abs_rad_s
Turn_Bias_Index
```

### 8.4 刺激指标

```text
Facing_AnyStim_Ratio_pct
Facing_AnyStim_MovingRatio_pct
Approaching_AnyStim_Ratio_pct
Approaching_AnyStim_MovingRatio_pct
Mean_StimError_abs_deg
Median_StimError_abs_deg
```

无刺激状态的刺激指标通常为 0。刺激效应比较应主要在 `State_Stimulus_On=1` 的状态内解释，或以同背景、同亮度的 no_stimulus 状态作为配对基线。

## 9. 推荐比较

### 9.1 采样和跟踪质控

先比较 wing 与 no_wing 是否存在系统性采样差异：

- `Mean_FT_Delta_ms`
- `FT_Delta_SD_ms`
- `DroppedFrame_Estimate`
- `Tracking_Reset_Count`
- 有效状态比例

如果组间跟踪质量不同，应先解决质控偏差，再解释行为差异。

### 9.2 wing 与 no_wing

可比较：

- 活动力
- 活动时速度
- 总距离
- 绝对角速度
- 路径直线度
- 朝向和接近刺激比例

优先使用每只果蝇的状态级值或条件均值，而不是把所有帧合并。

### 9.3 刺激效应

对同一只果蝇、同一背景和同一亮度，比较：

```text
stimulus - no_stimulus
```

主要观察：

- `Moving_Ratio_pct`
- `Mean_MovingSpeed_cm_s`
- `Mean_AngVel_abs_rad_s`
- `VR_Path_Straightness`

刺激状态内部再分析 facing 和 approaching。

### 9.4 颜色和亮度

颜色有 3 水平，亮度有 3 水平，建议保留为分类变量，不要默认 dark、medium、bright 在三种颜色中具有完全相同的物理亮度间隔。

分享配置中每种颜色使用独立校准值，因此统计和作图时既保留亮度标签，也保留 `State_Brightness` 数值。

## 10. 统计模型建议

样本量较小时，可先做每只果蝇的条件均值和配对图，再进行正式模型。

完整设计可使用混合效应模型：

```text
metric ~ wing_condition
       * State_Block
       * State_BG_Name
       * State_Brightness_Label
       + (1 | fly_id)
```

注意：

- 18 条件全交互参数较多，样本量不足时应简化模型。
- 比例指标可考虑二项模型，或在明确适用时进行变换。
- 距离和速度常右偏，可检查残差后使用对数变换或稳健模型。
- 多重比较需要校正。
- 报告效应量和置信区间，不只报告 p 值。

## 11. 当前画图脚本

### 11.1 轨迹图

```powershell
python plot_split_trajectory.py <主CSV或实验目录>
```

输出 `TrajectoryPlots/`。脚本使用 `VR_Fly_X_cm`、`VR_Fly_Y_cm` 和 `State_Index`，按状态绘图。

### 11.2 行为时间线

```powershell
python plot_facing_timeline.py <主CSV或实验目录>
```

输出 `BehaviorTimeline/`。当前脚本绘制速度、绝对角速度和状态背景带。文件名保留旧版 `facing` 名称，但当前不是独立的 facing/approaching 二值时间线。

### 11.3 极坐标方向图

```powershell
python plot_polar_preference.py <主CSV或实验目录>
```

输出 `PolarPreference/`。脚本只分析有刺激状态，直接使用 `Stim_Mapped_Angle_rad`、`Stim_VisualHalfWidth_rad` 和 `Stim_Facing_Any`。

## 12. 不推荐的做法

- 用打开相机的时间作为正式实验起点。
- 用 CSV 行号除以固定帧率代替 `Time_s`。
- 跨实验直接把同一 `State_Index` 当作同一视觉条件。
- 把每一帧当作独立生物学重复。
- 再次缩放已经修正为 `VR_ForwardGain=1.0` 的轨迹。
- 用固定视觉角宽覆盖 CSV 的 `Stim_VisualHalfWidth_rad`。
- 只保留平滑数据并覆盖原始列。
- 只看 `*_phase_summary.csv` 而不保留逐帧 CSV 和 FicTrac 原始数据。

## 13. 分析记录

每次正式分析建议记录：

- 纳入和排除的实验编号
- 排除原因
- 使用的代码版本
- 速度和角速度阈值
- 平滑窗口
- 异常帧规则
- 状态完整性标准
- 统计模型和多重比较方法
- 输出图和结果表的生成日期

这样可以保证后续重新分析时知道每一个结果来自哪一版数据和哪一套规则。
