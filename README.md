# CNKI Academic Writing V2.7.3

V2.7.3 是 V2.7 的**定点正确性补丁**：继续保持轻量流程；在 V2.7.2 的复杂公式双路径验证与强制 audit gate 基础上，只补 Round 2 回归真实漏报的两类问题——强归因引用落点核验、DOCX 表格结构内容与最终可视内容不一致。

## 保留的核心能力

- 课程要求 / 图片 / PDF / DOCX 模板 intake
- CNKI 检索与真实 evidence level
- Adaptive Evidence Budget：只为明确证据缺口定向读页段，不机械通读全部文献
- LOW / MEDIUM / HIGH 三档审计
- high-risk / material-medium claim 的具体 evidence locator
- Evidence-Safe Prose Polish + factual guard
- 真正 Visual QA：没看页面不能返回 layout `ok`
- 最终 DOCX 交付前复扫；不强制 SHA-256、manifest、复杂 carry-forward

## V2.7 保留的减法

- `references/`：从 16 份小文件合并为 5 份主题文档。
- `SKILL.md`：删掉大量与 reference 重复的解释，只保留硬规则、主流程和关键门禁。
- README / CHANGELOG：只保留当前使用需要的信息，不再重复历代版本说明。
- 回归测试提示词不再放进正式发行包。
- 大部分核心脚本逻辑沿用 V2.6.2 Final；仅 `precise_audit.py` 在 V2.7.1/V2.7.2/V2.7.3 做了定点增强。`assignment_intake.py` 的 `SCHEMA_VERSION=2.4` 是 intake 文件格式版本，不是 Skill 发布版本。

## V2.7.3 关键更新

- 保留 V2.7.2 的复杂/高风险关键公式双路径验证，以及 `precise_audit.py` / `layout_guard.py` 强制门禁。
- 新增**强归因引用落点队列**：`文献[n]指出/表明/证明…`、`已有研究…[n]`、`研究表明…[n]`、`据/根据文献[n]…` 等句型会被强制送入 Claim→Citation→Evidence 复核；“文献真实存在”不能替代“该引用真正支持当前句子”。
- 新增**DOCX 表格可视性静态预检**：非空单元格若所有文本显式白字/隐藏，且单元格背景不是深色，会生成 `table_visibility_findings` 并进入 audit gate；用于拦截“XML 有值、最终渲染肉眼为空”的交付缺陷。
- Final Visual QA 明确要求：表格页除了看边框/分页，还要核对非空结构化单元格在最终渲染中确实可见。
- 仍保持 schema `2.7`，不引入 OCR 全表比对、像素级表格识别或额外 manifest。

## 安装 / 升级

PowerShell 在仓库根目录运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

默认安装到：

```text
%USERPROFILE%\.agents\skills\cnki-academic-writing-v2
```

检查版本：

```powershell
Get-Content "$HOME\.agents\skills\cnki-academic-writing-v2\VERSION"
```

应显示：

```text
2.7.3
```

卸载：

```powershell
.\uninstall.ps1
```

## 图形配置器

`CNKI论文设置.exe` 用于生成/修改项目级 `assignment/workflow-config.json`。它独立于 Agent 本体；Agent 在项目中发现该 JSON 时会读取配置。

默认建议使用 **MEDIUM**：重点核验重要 claim，不把普通课程论文变成全量全文审计。

## 主要文件

```text
cnki-academic-writing-v2/
  SKILL.md
  VERSION
  agents/openai.yaml
  scripts/
    assignment_intake.py
    cnki_backend.py
    provenance_ledger.py
    precise_audit.py
    prose_polish.py
    layout_guard.py
  references/
    01-INTAKE-REQUIREMENTS.md
    02-RESEARCH-EVIDENCE.md
    03-AUDIT.md
    04-WRITING.md
    05-DELIVERY-QA.md
```

## 使用原则

V2.7.3 的停止原则：**如果一个新增机制主要提升“审计看起来有多专业”，却没有明显提升论文质量、真实性或交付稳定性，就不要加。**

发现小问题先记录；只有影响引用/事实、论文内容、视觉交付或流程稳定性的 bug 才值得修改 Skill。
