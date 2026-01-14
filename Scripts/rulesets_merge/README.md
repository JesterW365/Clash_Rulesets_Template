# Clash Rulesets Template - 规则集自动化生成工具

本项目是一个高效、智能的 Clash 规则集处理系统，旨在解决规则集维护过程中存在的来源不一、格式混乱、文件碎片化等痛点。它能够自动从多源抓取规则，并应用严格的标准化转换逻辑，生成性能最优、结构最精简的 Clash YAML 文件。

## 核心特性

- **一键自动化 (Full Automation)**：主脚本自动定位配置与补丁目录，完成抓取、转换、汇总、保存的全流程。
- **标准化优先 (Normalization First)**：智能决策引擎优先将规则提取并转化为极简的 `domain` 或 `ipcidr` 格式，舍弃冗余的非核心前缀。
- **智能防碎片化**：当 Group 内包含多种混合格式且规模较小时，自动退回到 `classical` 模式以保持单一文件，避免产生大量琐碎的小文件。
- **多源融合**：支持网络规则（URL）与本地补丁（`Supply_` 系列目录）的深度去重合并。
- **极致清洁**：内置强力清洗逻辑，自动移除注释、空行及 `payload:` 声明。

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
- **操作**：严格校验 `groupname`、`src` 条目及 `type`（必须为 classical/domain/ipcidr）。
- **输出**：结构化的 Group 信息字典。

### 2. `clean_content(content)`

- **操作**：清洗内容的“原子级”函数。
- **规则**：
  - 移除所有以 `#` 开头的注释。
  - 移除 `payload:` 行（不区分大小写）。
  - 移除行首的 `- ` 并剔除两端的额外空格及引号。

### 3. `merge_and_save_rulesets(base_results, supply_folder_path, target_output_dir)`

这是系统的**智能决策引擎**，其核心逻辑如下：

1. **提取核心 (Core Extract)**：仅提取 `DOMAIN`, `DOMAIN-SUFFIX`, `IP-CIDR`, `IP-SUFFIX` 四类前缀内容。其余类型在单一转换时会被舍弃。
2. **决策树**：
   - **分支 1 (归一转化)**：如果过滤后所有规则均能完美归入单一的 `domain` **或**单一的 `ipcidr` 池。
     - **动作**：强制输出为单一标准化类型文件，**不受 1200 条限制**。
   - **分支 2 (混合类型)**：如果核心规则中域名与 IP 共存。
     - **动作 (<= 1200 条)**：保持原始所有内容（不舍弃杂项），以单一 `classical` 文件输出，防止拆碎。
     - **动作 (> 1200 条)**：按核心类型拆分为 `_dm` 和 `_ip` 指向文件，此时舍弃不可转换的杂项以保证性能。

### 4. `convert_ruleset`

- 用于对单源数据进行初步格式化检测。
- **格式规范**：Classical 导出为无引号格式（如 `- DOMAIN,google.com`），Domain/IPCIDR 导出为单引号格式（如 `- 'google.com'`）。

## 输出规范

1. **缩进**：所有规则在 `payload:` 下统一使用 **2 个空格** 缩进。
2. **头部信息**：各文件包含 `Ruleset Type` 声明和 `Generated time` 生成时间戳。
3. **索引文件**：`rulesets.json` 记录了每个输出文件的总规则条数及判定类型，便于后续脚本查阅。

---

## 维护建议

- **新增补丁**：将补丁文件命名为 `supply_xxx.yaml` 放入 `SRC_rulesets/Supply_rulesets/` 下即可。
- **修改阈值**：如需调整拆分判定条数，修改 `merge_and_save_rulesets` 中的 `1200` 变量即可。

---

最后更新时间：2026-01-14
