# Changelog

## 2.7.3

基于 Round 2 BOSS 故障注入回归的最小补丁：

- 新增强归因引用落点复核：明确归因给某篇文献的句子必须核对该来源是否真正支持当前 proposition，不能只核题录真实性。
- `precise_audit.py` 对 `文献[n]指出/表明/证明…`、`已有研究…[n]`、`研究表明…[n]`、`据/根据文献[n]…` 等高收益模式标记 `attribution-evidence-check`，在 LOW/MEDIUM/HIGH 均纳入必审。
- 新增 DOCX 表格可视性静态预检：非空单元格若所有文本运行显式白色或隐藏、且单元格无深色底纹，则生成 `table_visibility_findings` 并由 audit gate 强制处置。
- Final Visual QA 增加“结构非空单元格 ↔ 最终渲染可见”检查，专门覆盖白字、隐藏文本、与背景同色等 XML 文本存在但肉眼为空的缺陷。
- 不扩展到全表 OCR/像素级 diff；静态预检负责高确定性异常，vision 负责最终页面确认。
- 继续保持 schema `2.7` 与 V2.7 的减法原则。

## 2.7.2

基于 BOSS-RUSH 故障注入回归的最小强化：

- 复杂/高风险关键公式不再允许“模型自己重推一遍”就判定通过；要求两条**结构独立**验证路径。
- `precise_audit.py` 为多概率尾项等明显复杂公式自动标记 `dual_validation_required`，并在 audit gate 中强制检查两种不同验证方法与具体记录。
- 明确区分“实现一致性”和“理论正确性”：同一错误公式生成的代码/CSV/图表一致不能充当第二条理论验证路径。
- `precise_audit.py scan/audit` 变为可运行时的强制门禁；手工审计不能替代，缺少旧 ledger 也不是跳过理由。
- `layout_guard.py` 同样不得被“已经看过页面”替代；视觉检查负责给出 visual status，guard 负责记录交付门禁。
- 继续保持 schema `2.7` 与 V2.7 的减法原则，不引入新状态机、hash 绑定或证据图谱。

## 2.7.1

基于实际论文回归的定点正确性补丁，不恢复被 V2.7 删除的重型机制：

- 修正 phase reference 的执行时序：必须在对应阶段开始前加载，事后回读只能补救，不能算按流程执行。
- 新增关键理论公式独立验证规则，明确“公式/代码/CSV/图表彼此一致”不等于理论正确。
- `precise_audit.py` 增加 DOCX OMML 数学文本提取、编号公式复核队列与明显括号失配检查。
- 新增未引用参考文献静态检查。
- Final QA 增加硬字数上限的计数口径规则，以及公式渲染语法检查。
- 扩展少量确定性强措辞（如“会高于”“必定”“一定”）的 strong-claim 触发。
- 审计 schema 仍保持 `2.7`，避免为兼容字段增加额外迁移复杂度。

## 2.7

结构精简版，基于已通过回归的 V2.6.2 Final：

- 将 16 份 reference 文档合并为 5 份主题文档。
- 大幅压缩 `SKILL.md`，主文件只保留硬规则、主流程、关键门禁与命令入口；详细规则按需读取 reference。
- 精简 README 与发行包内容，移除回归测试提示词。
- 保留 V2.6.2 的四个核心修复：真实 Visual QA 门禁、重要 claim 具体证据定位、final 文件复扫纪律、finding-specific rationale。
- 不引入 SHA-256 强绑定、视觉 manifest、复杂 carry-forward、证据图谱等重型机制。
- 核心脚本行为不做功能性重写，仅统一 V2.7 schema/release 标记；`assignment_intake.py` 保留独立 intake schema 2.4。

## 2.6.2 Final

完成减法收口并通过实际论文回归：Medium 未退化为全文审计；视觉模型逐页完成 Visual QA；重要 claim 泛定位会被拦；prose rationale 无模板化退化。
