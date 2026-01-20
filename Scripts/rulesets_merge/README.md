# Clash Rulesets Template - 规则集自动化生成工具

本项目是一个高效、智能的 Clash 规则集处理系统，旨在解决规则集维护过程中存在的来源不一、格式混乱、文件碎片化等痛点。它能够自动从多源抓取规则，并应用严格的标准化转换逻辑，生成性能最优、结构最精简的 Clash YAML 文件。

## 核心特性

- **一键自动化 (Full Automation)**：主脚本自动定位配置与补丁目录，完成抓取、转换、汇总、保存的全流程。
- **标准化优先 (Normalization First)**：智能决策引擎优先将规则提取并转化为极简的 `domain` 或 `ipcidr` 格式，舍弃冗余的非核心前缀。
- **域名极致优化**：支持基于 `+.abc.com` 语法的域名树级去重，自动移除被通配符覆盖的子域名。
- **智能防碎片化**：当 Group 内包含多种混合格式且规模较小时，自动退回到 `classical` 模式以保持单一文件，避免产生大量琐碎的小文件。
- **多源融合**：支持网络规则（URL）与本地补丁（`Supply_` 系列目录）的深度去重合并。
- **协议过滤与清洗**：内置黑名单机制，自动移除 `PROCESS-`, `GEOSITE`, `GEOIP` 等不支持的规则类型。

## 项目结构

```text
.
├── Scripts/
│   ├── manufacture.py           # [主入口] 总控生成脚本
│   ├── rulesets_merge_tools.py  # [工具链] 核心处理逻辑函数库
│   └── test_full_pipeline.py    # [验证] 全流程集成功测
├── SRC_rulesets/
│   ├── rulesets_src.yaml        # [配置] 规则源定义文件
│   └── Supply_rulesets/          # [补丁] 包含供本地覆盖的 supply_*.yaml
└── Generated_rulesets/          # [产出] 生成的目标文件 (运行后产生)
    ├── rulesets.json            # 产出索引及统计
    └── *.yaml                   # 生成的独立规则集文件
```

## 快速开始

### 环境依赖

- Python 3.8+
- 第三方库：`requests`, `pyyaml`
  ```bash
  pip install requests pyyaml
  ```

### 运行生成

在项目根目录运行以下命令：

```powershell
python Scripts/manufacture.py
```

程序将自动读取 `SRC_rulesets/rulesets_src.yaml` 并将结果输出至 `Generated_rulesets/`。

---

## 工具函数技术说明 (For Human & AI Tools)

核心逻辑集中在 `Scripts/rulesets_merge_tools.py` 中，主要函数接口如下：

### 1. `parse_rulesets_yaml(file_path)`

- **输入**：主配置 YAML 路径。
- **操作**：解析文件并严格校验 `groupname`、`src` 条目（支持 `classical/domain/ipcidr`）。
- **输出**：结构化的 Group 信息字典。

### 2. `clean_content(content)`

- **操作**：执行“原子级”清洗。
- **规则**：
  - 移除 `#` 注释、空行及 `payload:` 行。
  - 剔除行首的 `- ` 前缀及两端的引号。
  - **强制黑名单**：永久移除 `PROCESS-`, `GEOSITE`, `GEOIP` 开头的规则。

### 3. `optimize_domains(domain_list)`

- **操作**：域名去重与父级覆盖逻辑。
- **核心逻辑**：如果列表中存在 `+.abc.com`（通配符式根域名），则所有 `*.abc.com` 或 `sub.abc.com` 都会被视为已被覆盖并剔除，仅保留最高效的顶级规则。

### 4. `format_for_classical(rule, rule_type)`

- **操作**：将极简的域名/IP 规则还原为标准 Classical 格式。
- **转换示例**：
  - `+.google.com` -> `DOMAIN-SUFFIX,google.com`
  - `1.1.1.1` -> `IP-CIDR,1.1.1.1/32`

### 5. `merge_and_save_rulesets(base_results, supply_folder_path, target_output_dir)`

这是系统的**智能决策引擎**，其核心逻辑如下：

1. **自动合并补丁**：自动查找 `Supply_rulesets/` 下符合 `groupname` 的本地补丁并参与去重。
2. **决策树**：
   - **单态输出**：如果所有规则可完美归入单一 `domain` 或 `ipcidr` 池，则输出对应类型文件。
   - **混合保持 (<= 1200 条)**：保持混合格式，以单一 `classical` 文件输出，维持极简维护。
   - **混合拆分 (> 1200 条)**：自动拆分为 `{groupname}_dm.yaml` 和 `{groupname}_ip.yaml`，保障加载性能。

## 输出规范

1. **缩进与引号**：
   - `classical` 类型：内容不带引号（如 `- DOMAIN,google.com`）。
   - `domain/ipcidr` 类型：内容统一使用单引号包裹（如 `- 'google.com'`）。
2. **元数据**：各文件头部自动生成 `Ruleset Type`, `Generated time` 和 `Rule Count` 统计信息。
3. **索引同步**：同步更新 `rulesets.json` 作为下游 API 或脚本的索引依据。

---

## 维护建议

- **新增补丁**：将补丁文件命名为 `supply_xxx.yaml` 并定义对应的 `groupname` 放入 `SRC_rulesets/Supply_rulesets/` 下。
- **修改阈值**：如需调整拆分判定，代码中的 `1200` 变量为判定水位线。

---

最后更新时间：2026-01-20
