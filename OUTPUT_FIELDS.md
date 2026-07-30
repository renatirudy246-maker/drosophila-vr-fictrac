# 果蝇 VR 系统输出字段说明

更新日期：2026-07-15

本文档以分享包中的当前 `main.py`、`data_logger.py` 和 FicTrac 2.1.1 源码为准，说明原始输入、逐帧 CSV、状态汇总和图片输出。

## 1. 输出文件概览

一次完整实验通常产生：

| 文件 | 内容 |
| --- | --- |
| `fictrac-*.dat` | FicTrac 原始逐帧数据 |
| `fictrac-*.log` | FicTrac 启动、相机和运行日志 |
| `fictrac_config.txt` | 本次实验使用的 FicTrac 配置副本 |
| `experiment_settings.json` | 控制界面保存的本次实验参数 |
| `drosophila_exp_*.csv` | 逐帧实验数据，末尾附状态汇总 |
| `drosophila_exp_*_phase_summary.csv` | 独立状态汇总表，文件名保留旧版 `phase` 命名 |
| `live_trajectory.json` | 控制界面实时轨迹预览使用的临时状态 |
| `TrajectoryPlots/` | 状态轨迹图 |
| `BehaviorTimeline/` | 速度、角速度和状态时间线 |
| `PolarPreference/` | 有刺激状态的方向极坐标图 |

## 2. FicTrac 2.1.1 原始列

列顺序来自 [Trackball.cpp](fictrac-2.1.1/src/Trackball.cpp) 和 [data_header.txt](fictrac-2.1.1/doc/data_header.txt)。

UDP 文本通常带 `FT` 前缀：

```text
FT, col1, col2, ... col25
```

`.dat` 文件通常没有 `FT` 前缀。主程序会自动处理这两种情况。

| FicTrac 列号 | 含义 | 单位或说明 |
| --- | --- | --- |
| 1 | frame counter | 视频帧号 |
| 2-4 | delta rotation vector, camera frame | 相机坐标系下每帧旋转增量，rad |
| 5 | delta rotation error score | 当前旋转估计误差 |
| 6-8 | delta rotation vector, lab frame | 实验室坐标系下每帧旋转增量，rad |
| 9-11 | absolute rotation vector, camera frame | 相机坐标系下绝对旋转，rad |
| 12-14 | absolute rotation vector, lab frame | 实验室坐标系下绝对旋转，rad |
| 15 | integrated x position | 累积 X，rad；乘球半径得到 cm |
| 16 | integrated y position | 累积 Y，rad；乘球半径得到 cm |
| 17 | integrated animal heading | 果蝇朝向，rad |
| 18 | animal movement direction | 果蝇运动方向，rad |
| 19 | animal movement speed | 步长，rad/frame |
| 20 | integrated forward motion | 累积前进量，rad |
| 21 | integrated side motion | 累积侧移量，rad |
| 22 | timestamp | FicTrac 时间戳，ms |
| 23 | sequence counter | 序列号；跟踪重置后可能重新开始 |
| 24 | delta timestamp | 相邻输出之间的时间差，ms |
| 25 | alternate timestamp | 当天 0 点后的时间，ms |

当前主程序实际读取列 1、15-24，不读取列 25。

## 3. FicTrac 列到程序变量的映射

| FicTrac 列 | CSV或程序变量 | 计算 |
| --- | --- | --- |
| 1 | `FT_Frame` | 原始帧号 |
| 15 | `FT_X_cm` | column15 × `SPHERE_RADIUS_CM` |
| 16 | `FT_Y_cm` | column16 × `SPHERE_RADIUS_CM` |
| 17 | `FT_Heading_rad` | 原始 heading |
| 18 | `FT_MoveDir_rad` | 原始 movement direction |
| 19 | `FT_Speed_cm_s` | column19 × 球半径 ÷ column24 |
| 20 | `FT_Forward_cm` | column20 × 球半径 |
| 21 | `FT_Lateral_cm` | column21 × 球半径 |
| 22 | `FT_Timestamp_ms` | 原始 FicTrac 时间戳 |
| 23 | `FT_Seq` | 原始序列号 |
| 24 | `FT_Delta_ms` | 原始帧间隔 |

实验坐标系还执行以下方向变换：

```text
raw_fly_forward   = FT_Forward_cm
raw_fly_lateral   = -FT_Lateral_cm
Exp_Heading_rad   = -FT_Heading_rad
```

如果启用 `INVERT_ROTATION` 或 `INVERT_FORWARD`，还会按照配置进一步反向。平滑后的 heading 只用于显示，不写入 `Exp_Heading_rad`。

## 4. 实验时间的定义

`Time_s` 不是从打开相机或启动 FicTrac 时开始，而是从操作者在 VR 窗口按空格或单击鼠标后开始。

开始时程序会：

1. 清空 UDP 缓冲区中的旧数据包。
2. 建立 18 状态随机顺序。
3. 重置 CSV 记录器和 VR 轨迹。
4. 将空格后的第一个有效 FicTrac 数据包作为运动基线，该包不写入 CSV。
5. 从后续数据包开始累计正式实验时间。

时间增量优先使用：

```text
dt = FT_Delta_ms / 1000
Time_s[n] = Time_s[n-1] + dt
```

当 `FT_Delta_ms` 无效，或单次大于 500 ms 时，程序改用本机高精度接收时间差。这样相机提前打开不会增加正式实验时长，同时状态切换更贴近 FicTrac 的真实采样节奏。

`FT_Timestamp_ms` 保留 FicTrac 原始时间戳，适合与 `.dat`、调试视频和其他设备对齐。

## 5. 18 状态定义

默认状态矩阵为：

- 背景：white、green、red
- 亮度标签：dark、medium、bright
- 区块：no_stimulus、stimulus

无刺激 9 状态先随机排列，有刺激 9 状态再随机排列，合计 18 个状态。每个状态默认持续 `STATE_DURATION_S=20` 秒。

`Phase` 是旧版兼容字段，当前值与 `State_Index` 相同，均表示本次实验中的状态顺序 1-18。跨实验不要仅按 `Phase` 或 `State_Index` 匹配条件，应使用：

```text
State_Block
State_BG_Name
State_Brightness_Label
State_Stimulus_On
```

## 6. 逐帧 CSV 字段

当前分享配置下，每个逐帧数据行共有 88 列：

- 47 个固定实验字段
- 41 个 `Cfg_*` 配置快照字段

### 6.1 时间和状态字段

| 字段 | 含义 |
| --- | --- |
| `Time_s` | 按空格后累计的正式实验时间，s |
| `Phase` | 兼容字段，当前等于状态顺序 1-18 |
| `State_Index` | 本次实验中的状态顺序 1-18 |
| `State_Block` | `no_stimulus` 或 `stimulus` |
| `State_Elapsed_s` | 当前状态内已过时间，s |
| `State_BG_Name` | white、green 或 red |
| `State_BG_Color` | 背景 RGB 字符串 |
| `State_Brightness_Label` | dark、medium 或 bright |
| `State_Brightness` | 实际亮度系数 |
| `State_Stimulus_On` | 是否显示条纹，0/1 |

### 6.2 FicTrac 原始量

| 字段 | 含义 |
| --- | --- |
| `FT_Frame` | FicTrac 帧号 |
| `FT_Timestamp_ms` | FicTrac 原始时间戳 |
| `FT_Seq` | FicTrac 序列号 |
| `FT_Delta_ms` | FicTrac 相邻输出间隔 |
| `FT_X_cm`、`FT_Y_cm` | FicTrac 实验室坐标积分位置 |
| `FT_Heading_rad` | FicTrac 原始 heading |
| `FT_MoveDir_rad` | FicTrac 原始运动方向 |
| `FT_Speed_cm_s` | FicTrac column19 换算的速度 |
| `FT_Forward_cm` | 累积前进量 |
| `FT_Lateral_cm` | 累积侧移量 |

### 6.3 实验行为量

| 字段 | 含义 |
| --- | --- |
| `Exp_Heading_rad` | 方向处理后的实验 heading |
| `Exp_MoveDir_rad` | 当前 VR 世界位移方向；无位移时为空 |
| `Exp_Speed_cm_s` | 本项目用相邻累积运动量重新计算的速度 |
| `Exp_AngVel_rad_s` | wrapped heading 差分除以 dt |
| `Step_Distance_cm` | 当前帧身体运动步长 |
| `Is_Moving` | 速度或角速度达到阈值，0/1 |

主要公式：

```text
delta_forward = FT_Forward_cm[n] - FT_Forward_cm[n-1]
delta_lateral = transformed_lateral[n] - transformed_lateral[n-1]
Step_Distance_cm = sqrt(delta_forward^2 + delta_lateral^2)
Exp_Speed_cm_s = Step_Distance_cm / dt
Exp_AngVel_rad_s = wrapped_heading_delta / dt
Is_Moving = (Exp_Speed_cm_s > speed_threshold)
            OR (abs(Exp_AngVel_rad_s) > angular_velocity_threshold)
```

### 6.4 VR 世界坐标

| 字段 | 含义 |
| --- | --- |
| `VR_Fly_X_cm`、`VR_Fly_Y_cm` | 身体运动积分到 VR 世界后的果蝇位置 |
| `VR_ArenaCenter_Rel_X_cm`、`VR_ArenaCenter_Rel_Y_cm` | 从果蝇指向虚拟场中心的相对向量 |
| `VR_DistanceFromCenter_cm` | 上述向量长度 |
| `VR_ForwardGain` | VR 位移增益，当前主程序为 1.0 |

身体坐标位移会结合上一帧和当前帧 heading，以 4 个子步积分到世界坐标。当前 `FORWARD_GAIN=1.0`，因此不再对真实步长额外放大。

### 6.5 刺激几何和判定

| 字段 | 含义 |
| --- | --- |
| `Stim_Nearest_Angle_rad` | 当前 heading 与最近条纹中心方向的有符号角差 |
| `Stim_Mapped_Angle_rad` | 映射到前后刺激布局后的相对角，范围约为 [-π, π] |
| `Stim_Facing_Any` | heading 是否落入任一条纹当前视觉范围，0/1 |
| `Stim_Approaching_Any` | 果蝇正在运动且运动方向落入任一条纹视觉范围，0/1 |
| `Stim_VisualHalfWidth_rad` | 最近条纹当前渲染角宽的一半 |
| `Stim_RenderedWidth_rad` | 最近条纹当前完整渲染角宽 |
| `Stim_Anchor_Time_s` | 刺激世界建立时使用的无刺激末帧时间 |
| `Stim_Anchor_X_cm`、`Stim_Anchor_Y_cm` | 刺激锚定时果蝇的 VR 世界位置 |
| `Stim_Anchor_Heading_rad` | 刺激锚定时 heading |
| `Stim_Bar_Front_X_cm`、`Stim_Bar_Front_Y_cm` | 前方条纹固定世界坐标 |
| `Stim_Bar_Back_X_cm`、`Stim_Bar_Back_Y_cm` | 后方条纹固定世界坐标 |

第一个有刺激状态开始时，程序用无刺激区块最后一帧的位置和 heading 建立前后两个条纹，二者相差 π，并固定在 VR 世界中。

条纹动态角宽：

```text
raw_width = 2 × asin(BAR_HALF_WIDTH_CM / distance_to_bar)
Stim_RenderedWidth_rad = clamp(raw_width, 21.92°, 46.99°)
Stim_VisualHalfWidth_rad = Stim_RenderedWidth_rad / 2
```

判定公式：

```text
Stim_Facing_Any = abs(heading - bar_direction) <= visual_half_width

Stim_Approaching_Any =
    Exp_Speed_cm_s > MOVEMENT_SPEED_THRESHOLD
    AND abs(Exp_MoveDir_rad - bar_direction) <= visual_half_width
```

无刺激状态下，角度、宽度和两个判定列记录为 0；锚点与条纹世界坐标为空。

### 6.6 配置快照

每一帧后面附带 41 个 `Cfg_*` 列。它们记录本次实验实际使用的参数，分析时应优先使用这些列，而不是事后读取可能已经被修改的 `settings.json`。

```text
Cfg_SCREEN_FOV_DEG
Cfg_SPHERE_RADIUS_CM
Cfg_SIMULATION_MODE
Cfg_INVERT_ROTATION
Cfg_INVERT_FORWARD
Cfg_DEFAULT_BRIGHTNESS
Cfg_V_BAR_COUNT
Cfg_V_BAR_SPACING_DEG
Cfg_H_BAR_COUNT
Cfg_H_BAR_SPACING_CM
Cfg_VIRTUAL_WALL_DISTANCE_CM
Cfg_BAR_VISUAL_ANGLE_DEG
Cfg_BAR_HALF_WIDTH_CM
Cfg_SMOOTHING_FACTOR
Cfg_PHASE_1_DURATION
Cfg_PHASE_2_DURATION
Cfg_PHASE_3_DURATION
Cfg_MOVEMENT_SPEED_THRESHOLD
Cfg_MOVEMENT_ANG_VEL_THRESHOLD
Cfg_BG_COLOR
Cfg_BAR_COLOR
Cfg_STATE_DURATION_S
Cfg_STATE_RANDOM_SEED
Cfg_PRE_START_BG_COLOR
Cfg_PRE_START_BRIGHTNESS
Cfg_STATE_WHITE_COLOR
Cfg_STATE_GREEN_COLOR
Cfg_STATE_RED_COLOR
Cfg_STATE_WHITE_DARK_BRIGHTNESS
Cfg_STATE_WHITE_MEDIUM_BRIGHTNESS
Cfg_STATE_WHITE_BRIGHT_BRIGHTNESS
Cfg_STATE_GREEN_DARK_BRIGHTNESS
Cfg_STATE_GREEN_MEDIUM_BRIGHTNESS
Cfg_STATE_GREEN_BRIGHT_BRIGHTNESS
Cfg_STATE_RED_DARK_BRIGHTNESS
Cfg_STATE_RED_MEDIUM_BRIGHTNESS
Cfg_STATE_RED_BRIGHT_BRIGHTNESS
Cfg_STATE_BG_OPTIONS
Cfg_STATE_BRIGHTNESS_OPTIONS
Cfg_FORWARD_GAIN
Cfg_ARENA_RADIUS_CM
```

`Cfg_PHASE_1_DURATION`、`Cfg_PHASE_2_DURATION` 和 `Cfg_PHASE_3_DURATION` 只为兼容旧配置保留；当前 18 状态实验主要使用 `Cfg_STATE_DURATION_S`。

## 7. 状态汇总输出

独立汇总文件：

```text
drosophila_exp_YYYYMMDD_HHMMSS_phase_summary.csv
```

文件名中的 `phase` 是旧版兼容命名，当前每行对应一个 `State_Index`。主 CSV 末尾也会写入相同汇总，标记为：

```text
=== State Summary ===
```

### 7.1 基础和活动指标

| 字段 | 含义 |
| --- | --- |
| `Phase` | 当前状态顺序 1-18 |
| `State_Info` | 区块、背景、亮度和条纹开关组合说明 |
| `Duration_s` | 该状态最后时间减最早时间 |
| `Total_Frames` | 状态内记录帧数 |
| `Valid_Time_s` | `FT_Delta_ms` 累计时间 |
| `Moving_Frames`、`Still_Frames` | 活动和静止帧数 |
| `Moving_Ratio_pct`、`Still_Ratio_pct` | 活动和静止帧比例 |
| `Mean_Bout_Duration_s` | 平均连续活动片段时长 |
| `Mean_Stop_Duration_s` | 平均连续静止片段时长 |

### 7.2 距离、速度和转向

| 字段 | 含义 |
| --- | --- |
| `Total_Distance_cm` | `Step_Distance_cm` 总和 |
| `VR_Total_Distance_cm` | VR 世界轨迹相邻点距离总和 |
| `VR_Net_Displacement_cm` | 状态起点到终点直线距离 |
| `VR_Path_Straightness` | 净位移除以 VR 总路程 |
| `Mean_Speed_cm_s` | 全部帧平均速度 |
| `Mean_MovingSpeed_cm_s` | 仅活动帧平均速度 |
| `Median_Speed_cm_s`、`Peak_Speed_cm_s`、`Speed_SD_cm_s` | 速度分布指标 |
| `Mean_AngVel_abs_rad_s` | 绝对角速度均值 |
| `Median_AngVel_abs_rad_s`、`Peak_AngVel_abs_rad_s` | 绝对角速度统计 |
| `Signed_AngVel_Mean_rad_s` | 有符号角速度均值 |
| `Turn_Bias_Index` | 正角速度帧与负角速度帧的归一化差，范围 [-1,1] |

### 7.3 刺激指标

| 字段 | 含义 |
| --- | --- |
| `Facing_AnyStim_Frames` | `Stim_Facing_Any=1` 的帧数 |
| `Facing_AnyStim_Ratio_pct` | 朝向刺激帧占全部帧比例 |
| `Facing_AnyStim_MovingRatio_pct` | 朝向刺激且活动的帧占活动帧比例 |
| `Approaching_AnyStim_Frames` | `Stim_Approaching_Any=1` 的帧数 |
| `Approaching_AnyStim_Ratio_pct` | 朝刺激移动帧占全部帧比例 |
| `Approaching_AnyStim_MovingRatio_pct` | 朝刺激移动帧占活动帧比例 |
| `Mean_StimError_abs_deg` | 最近刺激角误差绝对值均值 |
| `Median_StimError_abs_deg` | 最近刺激角误差绝对值中位数 |
| `Min_StimError_abs_deg` | 最近刺激角误差绝对值最小值 |

### 7.4 空间和跟踪质控

| 字段 | 含义 |
| --- | --- |
| `Mean_DistanceFromCenter_cm` | 距虚拟场中心平均距离 |
| `Median_DistanceFromCenter_cm` | 距中心距离中位数 |
| `Max_DistanceFromCenter_cm` | 距中心最大距离 |
| `Center_Occupancy_pct` | 距中心不超过场半径 33% 的帧比例 |
| `Edge_Occupancy_pct` | 距中心达到场半径 80% 的帧比例 |
| `Mean_FT_Delta_ms`、`FT_Delta_SD_ms` | FicTrac 帧间隔均值和标准差 |
| `DroppedFrame_Estimate` | `FT_Delta_ms > 1.8 × 1000/180` 的异常间隔次数 |
| `Tracking_Reset_Count` | `FT_Seq` 不再递增的次数 |

`DroppedFrame_Estimate` 当前按 180 FPS 写死判断基准，它表示可疑长间隔次数，不等于精确丢失帧数。

## 8. 图片输出

### 8.1 `plot_split_trajectory.py`

输入关键列：

```text
State_Index
VR_Fly_X_cm
VR_Fly_Y_cm
```

输出到 `TrajectoryPlots/`：

- `00_all_states.png`：18 状态连续 VR 世界轨迹
- 每个有效状态一张独立轨迹图

### 8.2 `plot_facing_timeline.py`

文件名为旧版保留名称，当前实际绘制的是行为时间线。输入关键列：

```text
Time_s
State_Index
State_BG_Name
State_Brightness_Label
State_Brightness
State_Stimulus_On
Exp_Speed_cm_s
Exp_AngVel_rad_s
```

输出到 `BehaviorTimeline/`，包含平滑速度、绝对角速度和 18 状态背景带。当前脚本不单独绘制 `Stim_Approaching_Any` 时间线。

### 8.3 `plot_polar_preference.py`

只分析 `State_Stimulus_On=1` 的状态，核心使用：

```text
Stim_Mapped_Angle_rad
Stim_VisualHalfWidth_rad
Stim_Facing_Any
Exp_Speed_cm_s
Exp_AngVel_rad_s
```

极坐标柱状图使用活动帧方向分布；条纹扇区宽度优先使用 CSV 中 `Stim_VisualHalfWidth_rad` 的中位数，中心文字中的 facing ratio 直接来自 `Stim_Facing_Any`。

## 9. 分析时的优先级

1. FicTrac 原始追踪：`fictrac-*.dat`
2. 正式实验时间：`Time_s`
3. 采样质量：`FT_Delta_ms`、`FT_Seq`
4. 行为主量：`Exp_*`、`Step_Distance_cm`、`Is_Moving`
5. VR 轨迹：`VR_Fly_X_cm`、`VR_Fly_Y_cm`
6. 刺激关系：直接使用 `Stim_Facing_Any`、`Stim_Approaching_Any`、`Stim_VisualHalfWidth_rad`
7. 条件匹配：使用状态描述列，不要跨实验直接匹配 `State_Index`
8. 参数复现：优先使用同一 CSV 的 `Cfg_*` 字段
