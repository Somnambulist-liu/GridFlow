# GridFlow

<p align="center">
  <img src="resources/icon.png" alt="GridFlow Logo" width="128" height="128">
</p>

<p align="center"><strong>表格数据流式处理工具箱 — 轻量、快速、离线可用</strong></p>

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

| ✂️ | 🔗 |
|:---:|:---:|
| **表格拆分** | **表格合并** |
| 按指定字段拆分为独立文件或多个 Sheet | 多文件纵向合并，或多 Sheet 合并为单文件 |

| 🧹 | 🔄 |
|:---:|:---:|
| **数据去重** | **格式转换** |
| 按指定列检测并删除重复行，可选保留首/尾 | XLSX / CSV 批量互转 |

### 表格拆分
按任意列（地区、部门、产品等）将数据拆分为多个独立文件，或输出到单个文件的多个 Sheet 中。支持预设常用字段，一键选中。

### 表格合并
- **多文件模式**：选择多个 XLSX/CSV 文件，纵向追加合并，自动对齐列
- **多 Sheet 模式**：选择单个文件的多个 Sheet，合并为一个 Sheet

### 数据去重
选择一列或多列作为去重依据，预览重复数据后一键删除。支持保留首次出现或最后出现的记录。

### 格式转换
批量选择文件，一键在 XLSX 和 CSV 之间互转。支持指定输出目录，转换完成后自动打开。

---

## 技术架构

```
sheet2split/
├── main.py                 # 入口
├── app/
│   ├── main_window.py      # 根容器：首页 + 功能路由
│   ├── home_page.py        # 功能卡片首页
│   ├── theme.py            # 全局配色
│   ├── styles.py           # QSS 样式
│   ├── step_indicator.py   # 步骤指示器
│   ├── widgets/
│   │   └── common.py       # 共享 UI 组件
│   └── features/
│       ├── split.py        # 表格拆分
│       ├── merge.py        # 表格合并
│       ├── dedup.py        # 数据去重
│       └── convert.py      # 格式转换
└── core/
    ├── reader.py           # openpyxl 流式读取
    ├── splitter.py         # 拆分 Worker
    ├── merger.py           # 合并 Worker
    ├── deduper.py          # 去重 Worker
    └── converter.py        # 转换 Worker
```

- **GUI**：PySide6（Qt for Python），QSS 主题定制
- **数据处理**：openpyxl（read_only 流式读取 + Workbook 写入），无需 pandas
- **并发模型**：QThread Worker，progress / finished / error 信号驱动 UI 更新
- **打包**：PyInstaller 单文件 EXE，排除 30+ 未使用的 Qt 模块，最终体积约 62MB

---

## 开源协议

GridFlow 采用 **GNU Affero General Public License v3.0 (AGPLv3)** 开源协议。

核心要点：

- **可以**：自由使用、修改、分发，用于商业或非商业目的
- **必须**：保留原始版权声明，修改后的代码同样以 AGPLv3 开源
- **特别注意**：如果你修改了 GridFlow 并通过网络提供服务（包括 SaaS），也必须公开修改后的源代码

完整协议文本见 [LICENSE](LICENSE) 文件。

---

## 开发与构建

```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发版本
python main.py

# 生成图标
python generate_icon.py

# 打包为单文件 EXE
pyinstaller build.spec
```

**依赖项**：PySide6、openpyxl、pyinstaller（仅打包时需要）
