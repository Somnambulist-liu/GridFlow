# GridFlow @VERSION@

表格数据流式处理工具箱 —— 轻量、快速、离线可用。

## 下载 / Downloads

| 平台 | 文件 |
|------|------|
| 🪟 Windows x64 | `GridFlow-@VERSION@-Windows-x64.exe` |
| 🐧 Linux x86_64 | `GridFlow-@VERSION@-Linux-x86_64` |

Windows 版是单文件 EXE，双击即用，不需要安装 Python 或任何依赖。

## 🆕 本版本更新 / What's New

### 🛠️ 修复：自动更新后应用没有自动启动

从 3.5.2 及更早版本自动升级后，可能弹出

```
Security validation failure: unexpected name of application's home directory!
```

并且新版本没有自动打开。**更新文件其实已经装好了，手动双击 GridFlow 启动即可。**

原因是 PyInstaller 在 onefile 模式下会给自己设置 `_PYI_APPLICATION_HOME_DIR`、
`_PYI_ARCHIVE_FILE`、`_PYI_PARENT_PROCESS_LEVEL`、`_MEIPASS` 等内部变量，
更新脚本直接启动新版本时这些变量被继承，新版 bootloader 的父进程安全校验
（PyInstaller 6.22 起新增）因此误判并拒绝启动。本版本的修复：

- 启动新版本前清空上述变量，并设置官方开关 `PYINSTALLER_RESET_ENVIRONMENT=1`
- 覆盖安装改为最多 20 次重试，避免旧进程尚未退出就被判定为更新失败

> ⚠️ **从 3.5.2 升级到 3.5.3 时仍可能看到一次同样的提示** —— 因为执行更新动作的是
> 旧版本的程序。手动启动一次 GridFlow 即可，从 3.5.3 起后续更新都会正常自动重启。

### 📌 上一版回顾（v3.5.2）

界面全面优化：首页宽屏自适应、功能卡片键盘可达、暗色模式缺陷修复、
复选框与单选统一为「选中打勾」；设置与更新对话框重构（三张分组卡片、
更新流程三态、更新说明富文本渲染）。

### ✅ 验证

- 更新脚本与子进程环境：打桩断言 10 项 + 真实子进程验证（继承的 `_PYI_*` 全部被清理）
- 16 个功能场景 + 5 个拆分边界场景与旧版输出逐字节一致
- 界面改动逐屏截图核对（浅色 / 深色）；启动 127–131 ms、常驻内存约 48 MB

## 功能 / Features

### 数据处理

- **✂️ 表格拆分** — 按指定字段拆分为独立文件或多个 Sheet，支持自定义标题行、
  前置行/尾部行追加，保留单元格样式、合并单元格与公式
- **🔗 表格合并** — 多文件纵向合并，或多 Sheet 合并为单文件
- **🧹 数据去重** — 按指定列检测并删除重复行，可选保留首/尾
- **🔄 格式转换** — XLSX / CSV 批量互转

### 数据分析

- **🔍 数据筛选** — 按条件过滤行，支持 11 种运算符、AND/OR 组合
- **📋 列操作** — 保留/删除/重命名/重排列序，支持简单计算列
- **📊 透视表** — 行/列/值字段交叉聚合，计数/求和/平均/最值
- **✅ 数据校验** — 空值检测、异常值(IQR)、类型检查、重复行检测

### 系统特性

- 🔄 **自动更新** — 启动时自动检查 GitHub Releases，支持忽略版本、一键下载安装替换
- 🌓 深色/浅色主题切换
- 🌐 中英双语界面
- 📂 拖拽导入文件
- ⚡ openpyxl 流式读写，低内存占用
- 🔒 完全离线，数据不上传

## 🔐 校验 / Verify

下载后可用下面的命令核对文件完整性（每个产物同时附带 `.sha256` 文件）：

```bash
# Linux / macOS
sha256sum -c GridFlow-@VERSION@-Linux-x86_64.sha256
```

```powershell
# Windows PowerShell
Get-FileHash .\GridFlow-@VERSION@-Windows-x64.exe -Algorithm SHA256
```

与下方「SHA256 校验值」中的值一致即为完整文件。
