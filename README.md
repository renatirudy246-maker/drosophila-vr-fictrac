# 果蝇 VR 实验系统 / Drosophila VR with FicTrac 2.1.1

[中文](README.md) | [English](README_EN.md)

基于 Windows 和 FicTrac 2.1.1 的果蝇虚拟现实实验系统，用于接收球面跑步行为数据、在 U 形屏幕上呈现视觉刺激，并记录逐帧行为、状态汇总及分析图。

## 项目简介

本项目通过 UDP 接收 FicTrac 2.1.1 的追踪结果，将果蝇在球面跑台上的运动转换为虚拟空间中的位移与朝向，同时在 U 形屏幕上显示随机化视觉刺激。

当前装置中，U 形屏幕距离果蝇约 4 cm，软件默认视场角为 270°。屏幕的实际距离与参数 `VIRTUAL_WALL_DISTANCE_CM` 表示的虚拟墙距离含义不同，不能直接混用。

## 主要功能

- 按 FicTrac 2.1.1 输出格式解析 UDP 数据，列索引已经过源码核对
- 相机和 FicTrac 可提前启动，按下空格后才开始正式实验计时
- 18 个随机化视觉状态
- 记录 FicTrac 原始量、实验时间、VR 轨迹和刺激几何信息
- 输出逐帧 CSV 和状态级活动、轨迹、转向、朝向及接近行为汇总
- 提供轨迹图、行为时间线图和极坐标偏好图
- 默认使用相对路径，便于复制到其他电脑运行

## 仓库结构

| 路径 | 说明 |
| --- | --- |
| `launcher.py` | 实验控制主界面 |
| `main.py` | VR 主循环、FicTrac 解析、状态调度和数据记录 |
| `config.py` | 运行参数加载 |
| `data_logger.py` | 逐帧 CSV 和状态汇总字段定义 |
| `renderer.py` | U 形屏幕视觉刺激渲染 |
| `plot_*.py` | 离线绘图脚本 |
| `settings.json` | 可移植的默认配置 |
| `fictrac/` | 当前 FicTrac 配置和标定图像 |
| `fictrac-2.1.1/` | FicTrac 源码、头文件、文档、示例和构建文件 |
| `hardware/零件建模/` | 实验平台的 SolidWorks 零件和总装配模型 |
| `hardware/果蝇VR实验平台主要材料采购链接与价格.docx` | 主要材料、参考价格和采购链接 |
| `OUTPUT_FIELDS.md` | 完整输出字段与计算公式 |
| `DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md` | 数据质控、预处理和分析流程 |

实验数据、视频、日志、安装包和自动生成的编译目录不会写入 Git 历史。

## 安装

建议使用 Python 3.9-3.11。

```powershell
git clone https://github.com/renatirudy246-maker/drosophila-vr-fictrac.git
cd drosophila-vr-fictrac
python -m pip install -r requirements.txt
```

Windows 用户可直接下载并解压[最新 Release](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/latest)。运行包中包含 Git 仓库未收录的 FicTrac 可执行文件和 DLL。

## 运行与标定

```powershell
python launcher.py
```

更换电脑、相机或球体位置后，请在正式实验前完成以下检查：

1. 从控制界面打开 FicTrac 配置工具。
2. 重新检查相机源、球体 ROI、忽略区域和相机模型。
3. 确认 FicTrac 与控制程序使用相同的 UDP 端口，默认值为 `2000`。
4. 确认实际球体半径，默认配置为 `0.6 cm`。
5. 真实实验中保持 `SIMULATION_MODE=false`。

## 实验开始时序

相机和 FicTrac 可以提前启动。只有在 VR 窗口中按下空格后，正式实验时间才从零开始。

按下空格后，程序依次执行：

1. 清空开始前积压的 UDP 数据包；
2. 生成本次实验的 18 状态随机顺序；
3. 使用按键后的第一帧新 FicTrac 数据建立运动基线；
4. 从后续 FicTrac 帧差计算 `Time_s`、位移和轨迹，并写入 CSV。

因此，相机预热和实验准备时间不会被计入正式实验时间。

## 状态设计

默认实验包含：

- 3 种背景：白、绿、红
- 每种背景对应 3 个经过标定的亮度等级
- 前 9 个状态无条纹刺激，后 9 个状态有条纹刺激
- 每个状态 20 秒，总时长约 360 秒

两个区块内部的状态顺序分别随机化。`State_Index` 表示单次实验中的出现顺序，不是跨果蝇稳定的条件编号。跨实验分析应使用 `State_Block`、`State_BG_Name`、`State_Brightness_Label` 和 `State_Stimulus_On` 识别实验条件。

## 数据与绘图

实验结果默认写入 `exp_data/`。实验 CSV、视频和日志由 `.gitignore` 排除，应另行备份。

- [输出字段与计算公式](OUTPUT_FIELDS.md)
- [数据预处理与分析流程](DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md)

## FicTrac 源码与许可证

仓库中的 FicTrac 源文件保留原始 [CC BY-NC-SA 3.0 许可证](fictrac-2.1.1/LICENSE.txt)，署名和第三方说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本项目自编写的 Python 代码目前尚未选择单独的开源许可证。仓库公开并不自动授予额外的复制、修改或再分发权利。
