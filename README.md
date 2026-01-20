# 一个ClashMeta的模板和规则碎片的仓库，随意更新

项目的所有脚本由AI生成。

## 模板

默认模板为[Custom_templates/default_template.yaml](https://raw.githubusercontent.com/JesterW365/Clash_Rulesets_Template/master/Custom_templates/default_template.yaml "默认模板")

其基于Custom_templates/Parts中 \*\_default.yaml文件生成，处于不定时维护；

可以将headpart/dnspart/snifferpart/strategypart/rulespart修改为相同的后缀名用script进行合并成自己的模板，其中strategy和rules两个部分必须要有。

## 规则碎片

主要合并各个部分的上游规则至对应的规则组，减少规则集数量。

现有规则组查看[Generated_rulesets/rulesets.json](https://github.com/JesterW365/Clash_Rulesets_Template/raw/master/Generated_rulesets/rulesets.json "生成的规则组信息");
具体上游规则查看[SRC_rulesets/rulesets_src.yaml](https://github.com/JesterW365/Clash_Rulesets_Template/raw/master/SRC_rulesets/rulesets_src.yaml "源规则列表");
直接使用的上游规则查看[SRC_rulesets/Forked_rulesets/forked_rulesets.yaml](https://github.com/JesterW365/Clash_Rulesets_Template/raw/master/SRC_rulesets/Forked_rulesets/forked_rulesets.yaml "直接使用的上游规则列表");

上游规则主要为其他作者仓库的规则，引用将在最后列出，少部分为作者维护规则，置于Custom_rulesets/目录下，处于不定时维护；

删除了"PROCESS-"，和"GEOIP"，"GEOSITE"开头的规则，并尝试简化classical -> domain/ipcidr

- 舍弃了除 `DOMAIN`, `DOMAIN-SUFFIX`, `IP-CIDR`, `IP-SUFFIX` 之外的规则(因为上游规则也不常见其他类型，KEYWORD有较严重的问题也舍弃)；
- 超过1200条规则的规则集将根据domain/ipcidr进行拆分(如果可以的话)；
- 具体脚本逻辑请查看[Scripts/rulesets_merge/README.md](https://github.com/JesterW365/Clash_Rulesets_Template/blob/master/Scripts/rulesets_merge/README.md "规则集合并脚本说明")(Ai生成)

通过SRC_rulesets/Supply_rulesets/目录下的\*\_supply.yaml文件控制每个规则组的补充规则，处于不定时维护；

## 上游规则仓库

- [blackmatrix7](https://github.com/blackmatrix7/ios_rule_script)
- [anti-ad](https://anti-ad.net)
- [adrules.top](https://adrules.top)
- [Loyalsoldier](https://github.com/Loyalsoldier/clash-rules)
- [DustinWin](https://github.com/DustinWin/ruleset_geodata)
