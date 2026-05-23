"""Internationalization — string dictionaries + LangManager singleton.

Pattern mirrors ThemeManager: LangManager emits lang_changed, each widget
connects to the signal and calls _apply_lang() to refresh all visible text.
"""
from PySide6.QtCore import QObject, Signal, QSettings

APP_VERSION = "3.2.3"

# ── Chinese (default) ──────────────────────────────────────────────

ZH_CN = {
    # App shell
    "app.title": "GridFlow",
    "app.subtitle": "表格数据流式处理，轻量、快速、离线可用",
    "app.version": "v3.2.0",
    "btn.back": "← 首页",
    "btn.settings": "⚙ 设置",
    "btn.settings.tooltip": "设置",
    "btn.save": "保存",
    "btn.cancel": "取消",

    # Theme
    "theme.light": "🌙  浅色",
    "theme.dark": "☀️  深色",
    "theme.auto": "🖥️  自动",
    "theme.tooltip": "切换深色/浅色模式",

    # Home page — groups
    "home.group.data": "数据处理",
    "home.group.analysis": "数据分析",

    # Home page — warning
    "home.warning": "⚠️ 注意事项：除了表格拆分功能，其他功能目前还有小BUG存在，请谨慎使用！",

    # Home page — cards
    "card.split": "表格拆分",
    "card.split.desc": "按指定字段拆分为独立文件或多个 Sheet",
    "card.merge": "表格合并",
    "card.merge.desc": "多文件合并为一个或多 Sheet 合并",
    "card.dedup": "数据去重",
    "card.dedup.desc": "按指定列检测并删除重复数据行",
    "card.convert": "格式转换",
    "card.convert.desc": "XLSX / CSV 批量互转",
    "card.filter": "数据筛选",
    "card.filter.desc": "按条件过滤行，支持 11 种运算符",
    "card.columns": "列操作",
    "card.columns.desc": "重排、重命名、删除列及计算列",
    "card.pivot": "透视表",
    "card.pivot.desc": "交叉表分析，求和/计数/平均",
    "card.validate": "数据校验",
    "card.validate.desc": "空值检测、异常值发现、类型检查",

    # Settings dialog
    "settings.title": "⚙ 设置",
    "settings.language": "语言 / Language",
    "settings.language.zh": "中文",
    "settings.language.en": "English",
    "settings.general": "通用",
    "settings.output_dir": "默认输出目录",
    "settings.output_dir_placeholder": "选择默认输出目录...",
    "settings.auto_open_dir": "处理完成后自动打开输出目录",

    # Pipeline
    "pipeline.badge": "流水线: {n} 个输出",
    "pipeline.clear": "清空",

    # Split feature
    "split.step1": "选择文件",
    "split.step2": "拆分配置",
    "split.step3": "预览执行",
    "split.step_back": "←  上一步",
    "split.step_next": "下一步  →",
    "split.hero_title": "选择要拆分的 Excel 文件",
    "split.hero_sub": "支持 .xlsx / .xls 格式，可拖拽文件到此处",
    "split.drop_hint": "拖拽 Excel 文件到此处",
    "split.browse_btn": "浏览选择文件",
    "split.file_loaded": "✅ 已加载：{name}（共 {count} 个 Sheet）",
    "split.file_error": "❌ 无法读取文件：{error}",
    "split.select_sheet": "选择 Sheet",
    "split.select_sheet_placeholder": "请先选择文件",
    "split.split_column": "拆分字段",
    "split.select_column_placeholder": "请先选择 Sheet",
    "split.split_mode": "拆分模式",
    "split.mode_files": "拆分为独立文件",
    "split.mode_sheets": "拆分为多个 Sheet",
    "split.output_dir": "输出目录",
    "split.output_dir_placeholder": "默认与源文件相同目录",
    "split.file_naming": "文件命名",
    "split.prefix_placeholder": "前缀",
    "split.suffix_placeholder": "后缀",
    "split.naming_preview_hint": "预览：选择字段后将显示示例",
    "split.naming_preview_fmt": "预览：{sample}",
    "split.preview_title": "\U0001F50D  数据预览",
    "split.search_placeholder": "搜索过滤...",
    "split.col_value": "字段值",
    "split.col_rows": "行数",
    "split.col_pct": "占比",
    "split.summary_fmt": "共 {vc} 个不同值，{total_rows} 行数据",
    "split.info_banner_files": "将按「{column}」拆分为 {vc} 个文件，共 {total} 行数据",
    "split.info_banner_sheets": "将按「{column}」拆分为 {vc} 个 Sheet，共 {total} 行数据",
    "split.start_btn": "▶  开始拆分",
    "split.reading_data": "正在读取数据...",
    "split.done": "✓ 拆分完成",
    "split.error_fmt": "❌ 拆分失败：{error}",
    "split.field_item_fmt": "{val}  （{count} 行）  {bar}",
    "split.field_more_fmt": "... 共 {n} 个值",
    "split.field_btn_fmt": "{{{cn}}}  （{n}个）",
    "split.preset_none": "无",
    "split.field_tooltip": "点击查看该字段的所有值",
    "split.preserve_formulas": "保留原表公式（默认只保留数据）",
    "split.dialog_output_dir": "选择输出目录",

    # Merge feature
    "merge.mode": "合并模式",
    "merge.mode_files": "多文件合并",
    "merge.mode_sheets": "多 Sheet 合并",
    "merge.select_files": "选择文件（可多选）",
    "merge.add_files": "添加文件",
    "merge.clear": "清空",
    "merge.select_file": "选择文件",
    "merge.no_file": "未选择文件",
    "merge.select_sheets": "勾选要合并的 Sheet",
    "merge.output_dir": "输出目录",
    "merge.output_dir_placeholder": "选择输出目录",
    "merge.output_name": "输出文件名",
    "merge.start_btn": "▶  开始合并",
    "merge.need_two_files": "请至少添加 2 个文件",
    "merge.need_file_and_sheet": "请选择文件和至少一个 Sheet",
    "merge.read_error": "读取失败：{error}",
    "merge.error_fmt": "❌ 合并失败：{error}",
    "merge.dialog_select_excel": "选择 Excel 文件",
    "merge.dialog_select_output": "选择输出目录",

    # Dedup feature
    "dedup.select_file": "选择文件",
    "dedup.no_file": "未选择文件",
    "dedup.select_sheet": "选择 Sheet",
    "dedup.dedup_columns": "去重依据列（可多选）",
    "dedup.keep_mode": "重复行保留",
    "dedup.keep_first": "保留首次出现",
    "dedup.keep_last": "保留最后出现",
    "dedup.output_dir": "输出目录",
    "dedup.output_dir_placeholder": "默认与源文件相同目录",
    "dedup.start_btn": "▶  开始去重",
    "dedup.need_file_and_sheet": "请选择文件和 Sheet",
    "dedup.need_columns": "请选择至少一个去重列",
    "dedup.read_error": "读取失败：{error}",
    "dedup.error_fmt": "❌ 去重失败：{error}",
    "dedup.dialog_select_excel": "选择 Excel 文件",
    "dedup.dialog_select_output": "选择输出目录",

    # Convert feature
    "convert.target_format": "目标格式",
    "convert.fmt_xlsx_to_csv": "XLSX → CSV",
    "convert.fmt_csv_to_xlsx": "CSV → XLSX",
    "convert.select_files": "选择文件（可多选）",
    "convert.add_files": "添加文件",
    "convert.clear": "清空",
    "convert.output_dir": "输出目录",
    "convert.output_dir_placeholder": "选择输出目录",
    "convert.start_btn": "▶  开始转换",
    "convert.need_files": "请添加文件",
    "convert.error_fmt": "❌ 转换失败：{error}",
    "convert.dialog_select_files": "选择文件",
    "convert.dialog_select_output": "选择输出目录",

    # Common (shared)
    "common.open_output_dir": "\U0001F4C2 打开输出目录",
    "common.processing": "处理中...",

    # Generic
    "label.browse": "浏览",
    "label.select_file": "选择文件",
    "label.select_dir": "选择目录",
    "label.output": "输出",
    "label.input": "输入",
    "label.file": "选择文件",
    "label.sheet": "选择 Sheet",
    "label.output_dir": "输出目录",
    "label.no_file": "未选择文件",
    "label.default_out_dir": "默认与源文件相同目录",
    "label.file_dialog": "选择 Excel 文件",
    "label.dir_dialog": "选择输出目录",
    "label.read_error": "读取失败：{error}",
    "label.select_file_and_sheet": "请选择文件和 Sheet",

    # Filter
    "filter.condition_logic": "条件逻辑",
    "filter.filter_conditions": "筛选条件",
    "filter.add_condition": "+ 添加条件",
    "filter.logic_and": "AND（全部满足）",
    "filter.logic_or": "OR（任一满足）",
    "filter.start": "▶  开始筛选",
    "filter.value_placeholder": "值",
    "filter.max_placeholder": "最大值",
    "filter.add_valid_condition": "请至少添加一个有效条件",
    "filter.error_failed": "❌ 筛选失败：{error}",
    "filter.operator_eq": "等于",
    "filter.operator_neq": "不等于",
    "filter.operator_gt": "大于",
    "filter.operator_lt": "小于",
    "filter.operator_gte": "大于等于",
    "filter.operator_lte": "小于等于",
    "filter.operator_contains": "包含",
    "filter.operator_not_contains": "不包含",
    "filter.operator_between": "介于",
    "filter.operator_is_empty": "为空",
    "filter.operator_not_empty": "非空",

    # Columns
    "columns.column_ops": "列操作（勾选保留，拖拽排序）",
    "columns.rename_col": "重命名列",
    "columns.calc_col": "计算列",
    "columns.rename_btn": "应用",
    "columns.add_btn": "添加",
    "columns.calc_name_placeholder": "列名",
    "columns.calc_expr_placeholder": "公式，如 {{单价}} * {{数量}}",
    "columns.rename_placeholder": "新列名",
    "columns.rename_recorded": "已记录重命名: {old} → {new}",
    "columns.calc_preview": "计算列：",
    "columns.start": "▶  开始执行",
    "columns.keep_one": "请至少保留一列",
    "columns.error_failed": "❌ 操作失败：{error}",

    # Pivot
    "pivot.field_settings": "透视字段设置",
    "pivot.row_field": "行字段",
    "pivot.col_field": "列字段",
    "pivot.value_field": "值字段",
    "pivot.agg_method": "聚合方式",
    "pivot.agg_count": "计数",
    "pivot.agg_sum": "求和",
    "pivot.agg_avg": "平均",
    "pivot.agg_min": "最小",
    "pivot.agg_max": "最大",
    "pivot.start": "▶  生成透视表",
    "pivot.select_fields": "请选择行字段、列字段和值字段",
    "pivot.error_failed": "❌ 生成失败：{error}",

    # Validate
    "validate.check_types": "校验类型",
    "validate.empty_check": "空值检测（列空值率超过阈值）",
    "validate.threshold_label": "阈值 (%):",
    "validate.outlier_check": "异常值检测（IQR 四分位距法）",
    "validate.iqr_label": "IQR 倍数:",
    "validate.type_check": "类型一致性检查（混合 string/number 检测）",
    "validate.dup_check": "重复行检测",
    "validate.start": "▶  开始校验",
    "validate.select_one": "请至少选择一种校验类型",
    "validate.error_failed": "❌ 校验失败：{error}",
}

# ── English ────────────────────────────────────────────────────────

EN_US = {
    "app.title": "GridFlow",
    "app.subtitle": "Streamlined Spreadsheet Processing — Lightweight, Fast, Offline",
    "app.version": "v3.2.0",
    "btn.back": "← Home",
    "btn.settings": "⚙ Settings",
    "btn.settings.tooltip": "Settings",
    "btn.save": "Save",
    "btn.cancel": "Cancel",

    "theme.light": "🌙  Light",
    "theme.dark": "☀️  Dark",
    "theme.auto": "🖥️  Auto",
    "theme.tooltip": "Toggle dark/light mode",

    "home.group.data": "Data Processing",
    "home.group.analysis": "Data Analysis",
    "home.warning": "⚠️ Note: Except for Table Split, other features may have minor bugs. Please use with caution!",

    "card.split": "Table Split",
    "card.split.desc": "Split by fields into separate files or sheets",
    "card.merge": "Table Merge",
    "card.merge.desc": "Merge multiple files or sheets into one",
    "card.dedup": "Deduplication",
    "card.dedup.desc": "Detect and remove duplicate rows by columns",
    "card.convert": "Format Convert",
    "card.convert.desc": "Batch convert between XLSX and CSV",
    "card.filter": "Data Filter",
    "card.filter.desc": "Filter rows with 11 operators",
    "card.columns": "Column Ops",
    "card.columns.desc": "Reorder, rename, delete, and computed columns",
    "card.pivot": "Pivot Table",
    "card.pivot.desc": "Cross-tabulation with sum/count/avg",
    "card.validate": "Data Validate",
    "card.validate.desc": "Null detection, outlier detection, type checks",

    "settings.title": "⚙ Settings",
    "settings.language": "Language / 语言",
    "settings.language.zh": "中文",
    "settings.language.en": "English",
    "settings.general": "General",
    "settings.output_dir": "Default output directory",
    "settings.output_dir_placeholder": "Choose default output directory...",
    "settings.auto_open_dir": "Auto-open output directory after processing",

    "pipeline.badge": "Pipeline: {n} output(s)",
    "pipeline.clear": "Clear",

    # Split feature
    "split.step1": "Select File",
    "split.step2": "Split Config",
    "split.step3": "Preview & Run",
    "split.step_back": "←  Back",
    "split.step_next": "Next  →",
    "split.hero_title": "Select an Excel file to split",
    "split.hero_sub": "Supports .xlsx / .xls. Drag & drop files here.",
    "split.drop_hint": "Drop Excel file here",
    "split.browse_btn": "Browse File",
    "split.file_loaded": "✅ Loaded: {name} ({count} sheet(s))",
    "split.file_error": "❌ Cannot read file: {error}",
    "split.select_sheet": "Select Sheet",
    "split.select_sheet_placeholder": "Please select a file first",
    "split.split_column": "Split Column",
    "split.select_column_placeholder": "Please select a sheet first",
    "split.split_mode": "Split Mode",
    "split.mode_files": "Split to Separate Files",
    "split.mode_sheets": "Split to Multiple Sheets",
    "split.output_dir": "Output Directory",
    "split.output_dir_placeholder": "Same as source file by default",
    "split.file_naming": "File Naming",
    "split.prefix_placeholder": "Prefix",
    "split.suffix_placeholder": "Suffix",
    "split.naming_preview_hint": "Preview: shows after selecting a column",
    "split.naming_preview_fmt": "Preview: {sample}",
    "split.preview_title": "\U0001F50D  Data Preview",
    "split.search_placeholder": "Search filter...",
    "split.col_value": "Value",
    "split.col_rows": "Rows",
    "split.col_pct": "Pct.",
    "split.summary_fmt": "{vc} unique values, {total_rows} rows total",
    "split.info_banner_files": "Will split by '{column}' into {vc} files, {total} rows total",
    "split.info_banner_sheets": "Will split by '{column}' into {vc} sheets, {total} rows total",
    "split.start_btn": "▶  Start Split",
    "split.reading_data": "Reading data...",
    "split.done": "✓ Split Complete",
    "split.error_fmt": "❌ Split failed: {error}",
    "split.field_item_fmt": "{val}  ({count} row(s))  {bar}",
    "split.field_more_fmt": "... {n} values total",
    "split.field_btn_fmt": "{{{cn}}}  ({n})",
    "split.preset_none": "None",
    "split.field_tooltip": "Click to view all values of this field",
    "split.preserve_formulas": "Preserve original formulas (default: data only)",
    "split.dialog_output_dir": "Select Output Directory",

    # Merge feature
    "merge.mode": "Merge Mode",
    "merge.mode_files": "Merge Multiple Files",
    "merge.mode_sheets": "Merge Multiple Sheets",
    "merge.select_files": "Select Files (multi-select)",
    "merge.add_files": "Add Files",
    "merge.clear": "Clear",
    "merge.select_file": "Select File",
    "merge.no_file": "No file selected",
    "merge.select_sheets": "Check sheets to merge",
    "merge.output_dir": "Output Directory",
    "merge.output_dir_placeholder": "Select output directory",
    "merge.output_name": "Output Filename",
    "merge.start_btn": "▶  Start Merge",
    "merge.need_two_files": "Please add at least 2 files",
    "merge.need_file_and_sheet": "Please select a file and at least one sheet",
    "merge.read_error": "Read failed: {error}",
    "merge.error_fmt": "❌ Merge failed: {error}",
    "merge.dialog_select_excel": "Select Excel File",
    "merge.dialog_select_output": "Select Output Directory",

    # Dedup feature
    "dedup.select_file": "Select File",
    "dedup.no_file": "No file selected",
    "dedup.select_sheet": "Select Sheet",
    "dedup.dedup_columns": "Dedup Columns (multi-select)",
    "dedup.keep_mode": "Keep Row",
    "dedup.keep_first": "Keep First Occurrence",
    "dedup.keep_last": "Keep Last Occurrence",
    "dedup.output_dir": "Output Directory",
    "dedup.output_dir_placeholder": "Same as source file by default",
    "dedup.start_btn": "▶  Start Dedup",
    "dedup.need_file_and_sheet": "Please select a file and sheet",
    "dedup.need_columns": "Please select at least one dedup column",
    "dedup.read_error": "Read failed: {error}",
    "dedup.error_fmt": "❌ Dedup failed: {error}",
    "dedup.dialog_select_excel": "Select Excel File",
    "dedup.dialog_select_output": "Select Output Directory",

    # Convert feature
    "convert.target_format": "Target Format",
    "convert.fmt_xlsx_to_csv": "XLSX → CSV",
    "convert.fmt_csv_to_xlsx": "CSV → XLSX",
    "convert.select_files": "Select Files (multi-select)",
    "convert.add_files": "Add Files",
    "convert.clear": "Clear",
    "convert.output_dir": "Output Directory",
    "convert.output_dir_placeholder": "Select output directory",
    "convert.start_btn": "▶  Start Convert",
    "convert.need_files": "Please add files",
    "convert.error_fmt": "❌ Convert failed: {error}",
    "convert.dialog_select_files": "Select Files",
    "convert.dialog_select_output": "Select Output Directory",

    # Common (shared)
    "common.open_output_dir": "\U0001F4C2 Open Output Directory",
    "common.processing": "Processing...",

    # Generic
    "label.browse": "Browse",
    "label.select_file": "Select File",
    "label.select_dir": "Select Directory",
    "label.output": "Output",
    "label.input": "Input",
    "label.file": "Select File",
    "label.sheet": "Select Sheet",
    "label.output_dir": "Output Directory",
    "label.no_file": "No file selected",
    "label.default_out_dir": "Default: same as source directory",
    "label.file_dialog": "Select Excel File",
    "label.dir_dialog": "Select Output Directory",
    "label.read_error": "Read error: {error}",
    "label.select_file_and_sheet": "Please select a file and sheet",

    # Filter
    "filter.condition_logic": "Condition Logic",
    "filter.filter_conditions": "Filter Conditions",
    "filter.add_condition": "+ Add Condition",
    "filter.logic_and": "AND (All)",
    "filter.logic_or": "OR (Any)",
    "filter.start": "▶  Start Filter",
    "filter.value_placeholder": "Value",
    "filter.max_placeholder": "Max Value",
    "filter.add_valid_condition": "Please add at least one valid condition",
    "filter.error_failed": "❌ Filter failed: {error}",
    "filter.operator_eq": "Equals",
    "filter.operator_neq": "Not Equals",
    "filter.operator_gt": "Greater Than",
    "filter.operator_lt": "Less Than",
    "filter.operator_gte": "Greater or Equal",
    "filter.operator_lte": "Less or Equal",
    "filter.operator_contains": "Contains",
    "filter.operator_not_contains": "Not Contains",
    "filter.operator_between": "Between",
    "filter.operator_is_empty": "Is Empty",
    "filter.operator_not_empty": "Not Empty",

    # Columns
    "columns.column_ops": "Column Operations (check to keep, drag to reorder)",
    "columns.rename_col": "Rename Column",
    "columns.calc_col": "Computed Column",
    "columns.rename_btn": "Apply",
    "columns.add_btn": "Add",
    "columns.calc_name_placeholder": "Column Name",
    "columns.calc_expr_placeholder": "Formula, e.g. {Price} * {Qty}",
    "columns.rename_placeholder": "New Name",
    "columns.rename_recorded": "Rename recorded: {old} → {new}",
    "columns.calc_preview": "Computed columns: ",
    "columns.start": "▶  Start",
    "columns.keep_one": "Please keep at least one column",
    "columns.error_failed": "❌ Operation failed: {error}",

    # Pivot
    "pivot.field_settings": "Pivot Field Settings",
    "pivot.row_field": "Row Field",
    "pivot.col_field": "Column Field",
    "pivot.value_field": "Value Field",
    "pivot.agg_method": "Aggregation",
    "pivot.agg_count": "Count",
    "pivot.agg_sum": "Sum",
    "pivot.agg_avg": "Average",
    "pivot.agg_min": "Min",
    "pivot.agg_max": "Max",
    "pivot.start": "▶  Generate Pivot",
    "pivot.select_fields": "Please select row, column and value fields",
    "pivot.error_failed": "❌ Pivot failed: {error}",

    # Validate
    "validate.check_types": "Check Types",
    "validate.empty_check": "Empty Check (column empty rate exceeds threshold)",
    "validate.threshold_label": "Threshold (%):",
    "validate.outlier_check": "Outlier Detection (IQR method)",
    "validate.iqr_label": "IQR Multiplier:",
    "validate.type_check": "Type Consistency Check (mixed string/number)",
    "validate.dup_check": "Duplicate Row Detection",
    "validate.start": "▶  Start Validation",
    "validate.select_one": "Please select at least one check type",
    "validate.error_failed": "❌ Validation failed: {error}",
}


class LangManager(QObject):
    """Singleton managing UI language, mirrors ThemeManager pattern."""

    lang_changed = Signal(str)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._settings = QSettings("GridFlow", "GridFlow")
        self._lang = self._settings.value("language", "zh")
        self._strings = ZH_CN if self._lang == "zh" else EN_US

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def current_strings(self) -> dict:
        return self._strings

    def tr(self, key: str, **kwargs) -> str:
        """Translate a key. Supports format kwargs, e.g. tr('key', n=3)."""
        s = self._strings.get(key, key)
        if kwargs:
            return s.format(**kwargs)
        return s

    def set_lang(self, lang: str):
        """Set language ('zh' or 'en') and persist."""
        if lang == self._lang:
            return
        self._lang = lang
        self._settings.setValue("language", lang)
        self._strings = ZH_CN if lang == "zh" else EN_US
        self.lang_changed.emit(lang)

    def toggle(self):
        self.set_lang("en" if self._lang == "zh" else "zh")
