# GridFlow

<p align="center">
  <img src="resources/icon.png" alt="GridFlow Logo" width="128" height="128">
</p>

<p align="center"><strong>表格数据流式处理工具箱 — 轻量、快速、离线可用 | v3.2</strong></p>

---

## 初衷

在日常办公中，表格处理是最频繁的需求之一：按地区拆分销售报表、合并多个月的考勤数据、对客户名单去重、在 XLSX 和 CSV 之间转换格式……

现有的解决方案各有痛点：

- **Office / WPS 宏**：臃肿、卡顿，处理大文件时容易崩溃
- **在线工具**：数据上传到第三方服务器，存在隐私泄露风险
- **Python 脚本**：需要配置环境，对非技术人员不友好

GridFlow 由此诞生 —— **一个单文件 EXE，双击即用，所有数据在本地处理，不上传、不联网。** 基于 openpyxl 流式读写，处理十万行级别的表格也能保持低内存占用。

---

## 功能介绍

### 数据处理

| ✂️ | 🔗 |
|:---:|:---:|
| **表格拆分** | **表格合并** |
| 按指定字段拆分为独立文件或多个 Sheet | 多文件纵向合并，或多 Sheet 合并为单文件 |

| 🧹 | 🔄 |
|:---:|:---:|
| **数据去重** | **格式转换** |
| 按指定列检测并删除重复行，可选保留首/尾 | XLSX / CSV 批量互转 |

| 🔍 | 📋 |
|:---:|:---:|
| **数据筛选** | **列操作** |
| 按条件过滤行，支持 11 种运算符、AND/OR 组合 | 保留/删除/重命名/重排列序，支持简单计算列 |

| 📊 | ✅ |
|:---:|:---:|
| **透视表** | **数据校验** |
| 行/列/值字段交叉聚合，计数/求和/平均/最值 | 空值检测、异常值(IQR)、类型检查、重复行检测 |

### 表格拆分
按任意列（地区、部门、产品等）将数据拆分为多个独立文件，或输出到单个文件的多个 Sheet 中。支持预设常用字段，一键选中。可选保留原表公式（默认只保留数据值）。

### 表格合并
- **多文件模式**：选择多个 XLSX/CSV 文件，纵向追加合并，自动对齐列
- **多 Sheet 模式**：选择单个文件的多个 Sheet，合并为一个 Sheet

### 数据去重
选择一列或多列作为去重依据，预览重复数据后一键删除。支持保留首次出现或最后出现的记录。

### 格式转换
批量选择文件，一键在 XLSX 和 CSV 之间互转。支持指定输出目录，转换完成后自动打开。

### 数据筛选
按条件过滤数据行：等于、不等于、大于、小于、介于、包含、为空等 11 种运算符。支持 AND/OR 多条件组合，流式读取输出匹配结果。

### 列操作
勾选保留/删除列、拖拽调整列序、重命名列。支持简单计算列（如 `{单价} * {数量}`），包含公式预览。

### 透视表
选择行字段、列字段、值字段，聚合方式支持计数、求和、平均、最小、最大。输出含行列合计的完整交叉表。

### 数据校验
四种校验类型：空值检测（可设阈值百分比）、异常值检测（IQR 四分位距法）、类型一致性检查、重复行检测。生成详细校验报告 XLSX。

---

## 技术架构

```
sheet2split/
├── main.py                  # 入口
├── app/
│   ├── main_window.py       # 根容器：首页 + 功能路由
│   ├── home_page.py         # 功能卡片首页（分组 2×4 网格）
│   ├── theme.py             # 浅色/深色双配色方案
│   ├── theme_manager.py     # 动态主题管理器（单例，检测系统主题）
│   ├── i18n.py              # 国际化：202 键中英双字典 + LangManager 单例
│   ├── styles.py            # QSS 全局样式（动态配色）
│   ├── settings_dialog.py   # 设置对话框（语言切换）
│   ├── step_indicator.py    # 步骤指示器（拆分功能）
│   ├── settings.py          # QSettings 持久化
│   ├── pipeline.py          # 功能流水线（共享输出）
│   ├── presets.py           # 预设存取（JSON）
│   ├── platform_utils.py    # 跨平台文件操作
│   ├── widgets/
│   │   └── common.py        # 共享 UI 组件
│   └── features/
│       ├── split.py         # 表格拆分
│       ├── merge.py         # 表格合并
│       ├── dedup.py         # 数据去重
│       ├── convert.py       # 格式转换
│       ├── filter.py        # 数据筛选
│       ├── columns.py       # 列操作
│       ├── pivot.py         # 透视表
│       └── validate.py      # 数据校验
└── core/
    ├── reader.py            # openpyxl 流式读取
    ├── splitter.py          # 拆分 Worker
    ├── merger.py            # 合并 Worker
    ├── deduper.py           # 去重 Worker
    ├── converter.py         # 转换 Worker
    ├── filter_engine.py     # 筛选 Worker
    ├── column_ops.py        # 列操作 Worker
    ├── pivoter.py           # 透视表 Worker
    └── validator.py         # 校验 Worker
```

- **GUI**：PySide6（Qt for Python），QSS 主题定制，支持浅色/深色模式一键切换，中英双语界面
- **i18n**：LangManager 单例驱动运行时语言切换，202 个翻译键值覆盖全部 UI 文本
- **设置**：齿轮按钮 → 设置对话框，支持语言切换（中文/English），后续可扩展更多选项
- **数据处理**：openpyxl（read_only 流式读取 + Workbook 写入），无需 pandas
- **并发模型**：QThread Worker，progress / finished / error 信号驱动 UI 更新
- **打包**：PyInstaller，支持 Windows (.exe) / macOS (.app) / Linux，排除 30+ 未使用的 Qt 模块

---

## 开源协议

GridFlow 采用 **GNU Affero General Public License v3.0 (AGPLv3)** 开源协议。

核心要点：

- **可以**：自由使用、修改、分发，用于商业或非商业目的
- **必须**：保留原始版权声明，修改后的代码同样以 AGPLv3 开源
- **特别注意**：如果你修改了 GridFlow 并通过网络提供服务（包括 SaaS），也必须公开修改后的源代码

完整协议文本见 [LICENSE](LICENSE) 文件。

Copyright (C) 2025 Somnambulist-liu <liuzz_mang@163.com>

---

## 开发与构建

```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发版本
python main.py

# 生成图标
python generate_icon.py

# 打包（按平台选择对应 spec）
pyinstaller build_win.spec    # Windows
pyinstaller build_macos.spec  # macOS
pyinstaller build_linux.spec  # Linux
```

**依赖项**：PySide6、openpyxl、pyinstaller（仅打包时需要）
