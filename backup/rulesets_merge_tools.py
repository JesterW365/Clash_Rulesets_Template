import yaml
import os
import requests
import json
from datetime import datetime
import time

def clean_content(content):
    """
    清洗规则内容：移除注释、空行、空格行和 'payload:' 行。
    返回清洗后的行列表（纯内容，不带 '- ' 前缀）。
    """
    if isinstance(content, str):
        lines = content.splitlines()
    elif isinstance(content, list):
        lines = [str(item) for item in content]
    else:
        return []

    cleaned = []
    for line in lines:
        line = line.strip()
        # 1. 移除空行
        if not line:
            continue
        # 2. 移除注释
        if line.startswith('#'):
            continue
        # 3. 移除 payload: 行
        if line.lower() == 'payload:':
            continue
        
        # 4. 如果是以 '- ' 开头，提取核心内容
        if line.startswith('- '):
            core = line[2:].strip()
            # 再次检查 core 是否有效
            if core and not core.startswith('#'):
                cleaned.append(core.strip("'").strip('"'))
        else:
            # 纯文本行，直接处理
            cleaned.append(line.strip("'").strip('"'))
            
    return cleaned

def parse_rulesets_yaml(file_path):
    """
    解析主配置文件，增加严格的非空和合法类型校验。
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在。")
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"解析 YAML 文件时出错: {e}")
            return {}

    if not isinstance(data, dict):
        print("错误: YAML 文件根格式应为字典")
        return {}

    parsed_data = {}
    summary_lines = []
    file_name = os.path.basename(file_path)

    for group_title, group_content in data.items():
        # 检查 group_title 不能为空或空格
        if not group_title or not str(group_title).strip():
            continue

        if not isinstance(group_content, dict):
            continue
        
        # 检查 groupname 不能为空或空格
        group_name = group_content.get('groupname')
        if not group_name or not str(group_name).strip():
            continue
            
        src_list = group_content.get('src')
        if not isinstance(src_list, list):
            continue

        valid_rulesets = []
        for rs in src_list:
            if not isinstance(rs, dict):
                continue
            
            rs_name = rs.get('name')
            rs_type = rs.get('type')
            rs_url = rs.get('url')
            
            # 校验 rulesetname 不能为空
            if not rs_name or not str(rs_name).strip():
                continue
            # 校验 rulesettype 必须合法
            if rs_type not in ['classical', 'domain', 'ipcidr']:
                continue
            # 校验 ruleseturl 不能为空
            if not rs_url or not str(rs_url).strip():
                continue
                
            valid_rulesets.append({
                'name': rs_name,
                'type': rs_type,
                'url': rs_url
            })
        
        if valid_rulesets:
            parsed_data[group_title] = {
                'groupname': group_name,
                'rulesets': valid_rulesets
            }
            summary_lines.append(f"‘{group_title}’ - 包含 {len(valid_rulesets)} 个规则集")

    print(f"从 {file_name} 解析了 {len(parsed_data)} 个规则组，分别为：")
    for line in summary_lines:
        print(line)

    return parsed_data

def convert_ruleset(ruleset_name, ruleset_type, ruleset_content, bypass_threshold=False):
    """
    负责对单源内容进行初步解析和标准化。
    参数 bypass_threshold 用于控制是否在函数内部强制执行 1200 条转换逻辑。
    通常在 merge_and_save_rulesets 中调用时，我们会汇总后再定夺。
    """
    if ruleset_type not in ['classical', 'domain', 'ipcidr']:
        return []

    core_rules = clean_content(ruleset_content)
    if not core_rules:
        return []

    # 如果原始就是 domain 或 ipcidr 类型，直接返回（带引号）
    if ruleset_type in ['domain', 'ipcidr']:
        final_content = "\n".join([f"- '{r}'" for r in core_rules])
        return [{'name': ruleset_name, 'type': ruleset_type, 'content': final_content, 'raw_rules': core_rules}]

    # 如果是 classical，如果没有强制转换，先按原样 classical 返回
    # 延迟具体的转换逻辑到更高层 merge_and_save_rulesets
    if ruleset_type == 'classical':
        # 内部仍然保留原有的转换检测逻辑，供单函数调用时使用
        if bypass_threshold:
            # 这里的逻辑只有在独立调用或强制转换时使用
            # 保持现有逻辑不变以兼容旧的测试用例
            has_domain = any('DOMAIN' in r.upper() for r in core_rules)
            has_ip = any('IP-' in r.upper() for r in core_rules)
            if not has_domain and not has_ip:
                return [{'name': ruleset_name, 'type': 'classical', 'content': "\n".join([f"- {r}" for r in core_rules]), 'raw_rules': core_rules}]
            
            domain_rules = []
            ip_rules = []
            for r in core_rules:
                parts = r.split(',')
                if len(parts) < 2: continue
                prefix, val = parts[0].strip().upper(), parts[1].strip()
                if prefix == 'DOMAIN': domain_rules.append(val)
                elif prefix == 'DOMAIN-SUFFIX': domain_rules.append(f"+.{val}")
                elif prefix in ['IP-CIDR', 'IP-SUFFIX']: ip_rules.append(val)

            if has_domain and has_ip and len(core_rules) > 1200:
                res = []
                if domain_rules: res.append({'name': f"{ruleset_name}_dm", 'type': 'domain', 'content': "\n".join([f"- '{r}'" for r in domain_rules]), 'raw_rules': domain_rules})
                if ip_rules: res.append({'name': f"{ruleset_name}_ip", 'type': 'ipcidr', 'content': "\n".join([f"- '{r}'" for r in ip_rules]), 'raw_rules': ip_rules})
                return res
            
            if domain_rules and not ip_rules:
                return [{'name': ruleset_name, 'type': 'domain', 'content': "\n".join([f"- '{r}'" for r in domain_rules]), 'raw_rules': domain_rules}]
            if ip_rules and not domain_rules:
                return [{'name': ruleset_name, 'type': 'ipcidr', 'content': "\n".join([f"- '{r}'" for r in ip_rules]), 'raw_rules': ip_rules}]

        # 默认模式：返回标准化的 Classical
        return [{'name': ruleset_name, 'type': 'classical', 'content': "\n".join([f"- {r}" for r in core_rules]), 'raw_rules': core_rules}]

    return []

    return []

    return []

def fetch_ruleset_content(url, retries=3):
    """从网络获取规则集内容"""
    for i in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"获取 {url} 失败 ({i+1}/{retries}): {e}")
            time.sleep(1)
    return None

def parse_supply_files(supply_dir):
    """解析指定目录下的 supply_*.yaml 文件"""
    supply_data = {} # {group_name: [ruleset_info, ...]}
    if not os.path.exists(supply_dir):
        return supply_data

    for filename in os.listdir(supply_dir):
        if filename.startswith('supply_') and filename.endswith('.yaml') and filename != 'supply_.yaml':
            file_path = os.path.join(supply_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 基础解析获取元数据
            try:
                # 简单加载以获取字段，因为 content 可能是带注释或不规范的
                raw_data = yaml.safe_load(content)
                if not raw_data or not isinstance(raw_data, dict): continue
                
                group_name = raw_data.get('groupname')
                rs_type = raw_data.get('type')
                payload = raw_data.get('payload')
                
                if not group_name or not rs_type or not payload: continue
                
                # 处理 ruleset_name
                rs_name = raw_data.get('name')
                if not rs_name or str(rs_name).strip() == "":
                    rs_name = os.path.splitext(filename)[0]
                
                # 处理 payload: 使用 clean_content 统一清洗
                cleaned_rs_content = clean_content(content)
                if not cleaned_rs_content: continue
                
                # 特殊逻辑：如果在原始文本中（排除空行和注释后）存在没有 '- ' 前缀的内容，则舍弃
                # parse_supply_files 的语义是处理 YAML 格式。这里我们要二次验证。
                lines_for_check = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith('#') and l.strip().lower() != 'payload:']
                if any(not l.startswith('- ') for l in lines_for_check):
                    continue
                
                # 转换为标准格式以便后续使用 convert_ruleset
                # convert_ruleset 会自动应用引号规则
                rs_info = {
                    'name': rs_name,
                    'type': rs_type,
                    'content': "\n".join([f"- {r}" for r in cleaned_rs_content])
                }
                
                if group_name not in supply_data:
                    supply_data[group_name] = []
                supply_data[group_name].append(rs_info)
                
            except Exception as e:
                print(f"解析补丁文件 {filename} 出错: {e}")
                continue
                
    return supply_data

def merge_and_save_rulesets(base_results, supply_folder_path, target_output_dir):
    """
    重写后的逻辑：全 Group 汇总后再进行 1200 条阈值判断。
    """
    if not os.path.exists(target_output_dir):
        os.makedirs(target_output_dir)

    supply_dict = parse_supply_files(supply_folder_path)
    final_output_info = {}
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for group_title, group_info in base_results.items():
        group_name = group_info['groupname']
        rulesets = group_info['rulesets']
        
        # 用于累积该组所有的原始规则行
        all_raw_rules = [] # 存储 classical 格式的行
        
        # A. 提取网络规则
        for rs in rulesets:
            content = fetch_ruleset_content(rs['url'])
            if content:
                # 统一获取清洗后的核心内容
                all_raw_rules.extend(clean_content(content))
            else:
                print(f"警告: 规则集 {rs['name']} 内容为空或获取失败。")
        
        # B. 提取 Supply 规则
        if group_name in supply_dict:
            for s_rs in supply_dict[group_name]:
                # s_rs['content'] 已经是 clean 且 standard 的 YAML 字符串
                all_raw_rules.extend(clean_content(s_rs['content']))

        # 去重，保持大致顺序
        all_raw_rules = list(dict.fromkeys(all_raw_rules))
        if not all_raw_rules: continue

        total_count = len(all_raw_rules)
        
        # --- 最终版决策逻辑：单一转换优先 ---
        valid_outputs = [] # [{'type':..., 'rules': [...]}]
        dm_rules = []
        ip_rules = []
        
        # 统计经过“标准化提取”后能保留下来的核心规则
        for r in all_raw_rules:
            parts = r.split(',')
            if len(parts) >= 2:
                prefix, val = parts[0].strip().upper(), parts[1].strip()
                # 仅保留这四类核心规则用于转换
                if prefix == 'DOMAIN': dm_rules.append(val)
                elif prefix == 'DOMAIN-SUFFIX': dm_rules.append(f"+.{val}")
                elif prefix in ['IP-CIDR', 'IP-SUFFIX']: ip_rules.append(val)
                # 其余前缀（KEYWORD, PROCESS-NAME 等）在这里被“舍弃”不计入池子
            else:
                # 已经是纯内容行
                if '/' in r or (r.replace('.','').isdigit()): ip_rules.append(r)
                else: dm_rules.append(r)

        # 决策逻辑如下：
        
        # 1. 如果通过舍弃非核心规则后，能归属到单一的 domain 或 ipcidr 类型
        if dm_rules and not ip_rules:
            valid_outputs.append({'type': 'domain', 'rules': dm_rules})
        elif ip_rules and not dm_rules:
            valid_outputs.append({'type': 'ipcidr', 'rules': ip_rules})
            
        # 2. 如果核心规则（Domain 和 IP）依然是混合的
        elif dm_rules and ip_rules:
            # 判断原数据总数是否超过 1200 条
            if total_count <= 1200:
                # 规则少且混合：为了不产生碎片文件，退回到 Classical（包含所有原始行，不舍弃任何内容）
                valid_outputs.append({'type': 'classical', 'rules': all_raw_rules})
            else:
                # 规则多：进行规范化拆分（此时非核心规则会被舍弃）
                valid_outputs.append({'type': 'domain', 'rules': dm_rules})
                valid_outputs.append({'type': 'ipcidr', 'rules': ip_rules})
        
        # 3. 如果通过过滤后核心规则池为空（比如这个组全是 KEYWORD 或 PROCESS-NAME）
        elif not dm_rules and not ip_rules:
            # 按原样 Classical 输出
            valid_outputs.append({'type': 'classical', 'rules': all_raw_rules})

        # --- 保存阶段 ---
        type_suffixes = {'classical': '', 'domain': '_dm', 'ipcidr': '_ip'}

        for out in valid_outputs:
            r_type = out['type']
            rules = out['rules']
            
            # 文件名逻辑
            if len(valid_outputs) == 1:
                out_name = group_name
            else:
                suffix = type_suffixes.get(r_type, f"_{r_type}")
                out_name = f"{group_name}{suffix}"
            
            file_path = os.path.join(target_output_dir, f"{out_name}.yaml")
            
            def finalize_fmt(rule, rt):
                if rt == 'classical': return f"  - {rule}"
                else: return f"  - '{rule}'"

            header = f"# Ruleset Type:  {r_type}\n# Generated time: {generated_time}\npayload:\n"
            content_payload = "\n".join([finalize_fmt(r, r_type) for r in rules])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(header + content_payload)
            
            final_output_info[out_name] = {"group_type": r_type, "rule_count": len(rules)}

    json_path = os.path.join(target_output_dir, 'rulesets.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final_output_info, f, ensure_ascii=False, indent=2)

    print(f"合并完成，共生成 {len(final_output_info)} 个规则文件，详情见 {json_path}")
    return final_output_info

