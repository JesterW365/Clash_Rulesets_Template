import yaml
import os
import requests
import json
from datetime import datetime
import time

# ================= 工具函数区 =================

def clean_content(content):
    """
    清洗规则内容：
    1. 移除注释、空行、空格行和 'payload:' 行。
    2. 移除引号并提取核心内容（去除 '- ' 前缀）。
    3. 永久移除 'PROCESS-', 'GEOSITE', 'GEOIP' 开头的规则。
    """
    if isinstance(content, str):
        lines = content.splitlines()
    elif isinstance(content, list):
        lines = [str(item) for item in content]
    else:
        return []

    cleaned = []
    banned_prefixes = ('PROCESS-', 'GEOSITE', 'GEOIP')

    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('#'): continue
        if line.lower() == 'payload:': continue
        
        core = ""
        if line.startswith('- '):
            temp_core = line[2:].strip()
            if temp_core and not temp_core.startswith('#'):
                core = temp_core.strip("'").strip('"')
        else:
            core = line.strip("'").strip('"')
            
        if core:
            upper_core = core.upper()
            if upper_core.startswith(banned_prefixes):
                continue
            cleaned.append(core)
            
    return cleaned

def optimize_domains(domain_list):
    """域名去重核心逻辑：+.abc.com 覆盖 *.abc.com"""
    temp_set = set(domain_list)
    suffix_roots = set()
    
    for d in temp_set:
        if d.startswith('+.'):
            suffix_roots.add(d[2:].lower())
    
    final_domains = []
    for d in sorted(list(temp_set)):
        if d.startswith('+.'):
            final_domains.append(d)
            continue
            
        check_str = d.lower()
        if check_str.startswith('*.'):
            check_str = check_str[2:]
            
        parts = check_str.split('.')
        is_covered = False
        for i in range(len(parts)):
            sub_domain = ".".join(parts[i:])
            if sub_domain in suffix_roots:
                is_covered = True
                break
        
        if not is_covered:
            final_domains.append(d)
            
    return final_domains

def format_for_classical(rule, rule_type):
    """还原 Classical 格式"""
    if rule_type == 'domain':
        if rule.startswith('+.'):
            return f"DOMAIN-SUFFIX,{rule[2:]}"
        else:
            return f"DOMAIN,{rule}"
    elif rule_type == 'ip':
        if '/' in rule:
            return f"IP-CIDR,{rule}"
        else:
            return f"IP-CIDR,{rule}/32"
    return rule

def parse_rulesets_yaml(file_path):
    """解析主配置文件"""
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在。")
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"解析 YAML 文件时出错: {e}")
            return {}

    parsed_data = {}
    if not isinstance(data, dict): return {}

    for group_title, group_content in data.items():
        if not group_title or not str(group_title).strip(): continue
        if not isinstance(group_content, dict): continue
        
        group_name = group_content.get('groupname')
        if not group_name: continue
        src_list = group_content.get('src')
        if not isinstance(src_list, list): continue

        valid_rulesets = []
        for rs in src_list:
            if not isinstance(rs, dict): continue
            if not rs.get('name') or not rs.get('url'): continue
            
            valid_rulesets.append({
                'name': rs.get('name'),
                'type': rs.get('type', 'classical'),
                'url': rs.get('url')
            })
        
        if valid_rulesets:
            parsed_data[group_title] = {
                'groupname': group_name,
                'rulesets': valid_rulesets
            }

    print(f"已解析配置，共 {len(parsed_data)} 个规则组。")
    return parsed_data

def fetch_ruleset_content(url, retries=3):
    """下载规则内容"""
    print(f"  -> 正在下载: {url} ...", end="", flush=True)
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(" [成功]")
                return response.text
            else:
                print(f" [{response.status_code}]", end="", flush=True)
        except Exception as e:
            if i < retries - 1:
                print(f" [R{i+1}]", end="", flush=True)
            else:
                print(" [失败]")
            time.sleep(1)
    return None

def parse_supply_files(supply_dir):
    """
    解析补丁文件 (修正版)
    仅读取 payload 列表，避免读取到 header 元数据
    """
    supply_data = {} 
    if not os.path.exists(supply_dir):
        return supply_data

    for filename in os.listdir(supply_dir):
        if filename.startswith('supply_') and filename.endswith('.yaml'):
            file_path = os.path.join(supply_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw = yaml.safe_load(f)
                
                if not raw or not isinstance(raw, dict): continue
                
                group_name = raw.get('groupname')
                payload = raw.get('payload') # 获取 list 对象
                
                if not group_name or not payload or not isinstance(payload, list): 
                    continue

                # 传入 list，clean_content 会清洗 list 中的每一项
                cleaned = clean_content(payload)
                if not cleaned: continue

                rs_info = {
                    'name': raw.get('name', filename),
                    'content': "\n".join([f"- {r}" for r in cleaned])
                }
                
                if group_name not in supply_data:
                    supply_data[group_name] = []
                supply_data[group_name].append(rs_info)
                
            except Exception as e:
                print(f"解析补丁 {filename} 出错: {e}")
                continue
    return supply_data

# ================= 核心逻辑区 =================

def merge_and_save_rulesets(base_results, supply_folder_path, target_output_dir):
    if not os.path.exists(target_output_dir):
        os.makedirs(target_output_dir)

    supply_dict = parse_supply_files(supply_folder_path)
    final_output_info = {}
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for group_title, group_info in base_results.items():
        group_name = group_info['groupname']
        rulesets = group_info['rulesets']
        
        print(f"\n[处理中] 规则组: {group_title} ({group_name})")
        
        all_raw_rules = [] 
        
        # 1. 下载
        for rs in rulesets:
            content = fetch_ruleset_content(rs['url'])
            if content:
                all_raw_rules.extend(clean_content(content))
        
        # 2. 合并补丁
        if group_name in supply_dict:
            print(f"  -> 合并本地补丁: {len(supply_dict[group_name])} 个文件")
            for s_rs in supply_dict[group_name]:
                all_raw_rules.extend(clean_content(s_rs['content']))

        if not all_raw_rules:
            print("  -> 无有效规则，跳过。")
            continue

        # 3. 分类 (Raw -> Standard)
        dm_pool = []
        ip_pool = []
        
        for r in all_raw_rules:
            parts = r.split(',')
            if len(parts) >= 2:
                prefix, val = parts[0].strip().upper(), parts[1].strip()
                if prefix == 'DOMAIN': dm_pool.append(val)
                elif prefix == 'DOMAIN-SUFFIX': dm_pool.append(f"+.{val}")
                elif prefix in ['IP-CIDR', 'IP-CIDR6', 'IP-SUFFIX']: ip_pool.append(val)
            else:
                # 纯内容判断修正：排除带空格的行（避免 key: value 被误判为 IPv6）
                if ('/' in r) or (r.replace('.','').isdigit()) or (':' in r and ' ' not in r):
                    ip_pool.append(r)
                else:
                    dm_pool.append(r)

        # 4. 去重与优化
        count_before = len(dm_pool) + len(ip_pool)
        ip_pool = sorted(list(set(ip_pool)))
        dm_pool = optimize_domains(dm_pool)
        
        count_after = len(dm_pool) + len(ip_pool)
        print(f"  -> 规则优化: {count_before} -> {count_after} (去重: {count_before - count_after})")

        # 5. 输出决策
        valid_outputs = [] 
        total_count = len(dm_pool) + len(ip_pool)
        
        if dm_pool and not ip_pool:
            valid_outputs.append({'type': 'domain', 'rules': dm_pool})
        elif ip_pool and not dm_pool:
            valid_outputs.append({'type': 'ipcidr', 'rules': ip_pool})
        elif dm_pool and ip_pool and total_count > 1200:
            valid_outputs.append({'type': 'domain', 'rules': dm_pool})
            valid_outputs.append({'type': 'ipcidr', 'rules': ip_pool})
        else: # 混合且少量 -> Classical
            combined_rules = []
            for d in dm_pool: combined_rules.append(format_for_classical(d, 'domain'))
            for i in ip_pool: combined_rules.append(format_for_classical(i, 'ip'))
            valid_outputs.append({'type': 'classical', 'rules': combined_rules})

        # 6. 保存
        type_suffixes = {'classical': '', 'domain': '_dm', 'ipcidr': '_ip'}
        for out in valid_outputs:
            r_type = out['type']
            rules = out['rules']
            
            if len(valid_outputs) == 1:
                out_name = group_name
            else:
                suffix = type_suffixes.get(r_type, f"_{r_type}")
                out_name = f"{group_name}{suffix}"
            
            file_path = os.path.join(target_output_dir, f"{out_name}.yaml")
            
            def finalize_fmt(rule, rt):
                if rt == 'classical': return f"  - {rule}"
                else: return f"  - '{rule}'"

            header = f"# Ruleset Type:  {r_type}\n# Generated time: {generated_time}\n# Rule Count: {len(rules)}\npayload:\n"
            content_payload = "\n".join([finalize_fmt(r, r_type) for r in rules])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(header + content_payload)
            
            final_output_info[out_name] = {"group_type": r_type, "rule_count": len(rules)}

    json_path = os.path.join(target_output_dir, 'rulesets.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final_output_info, f, ensure_ascii=False, indent=2)

    print(f"\n全部完成！共生成 {len(final_output_info)} 个文件。")
    return final_output_info