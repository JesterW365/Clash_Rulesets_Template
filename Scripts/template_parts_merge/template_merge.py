import os
import sys

def merge_template(template_name, parts_dir, head_name, dns_name, sniffer_name=None, strategy_name='default', rules_name='default'):
    """
    根据传入的 7 个参数合并模板片段。
    """
    
    # 1. 校验参数
    template_name = template_name.strip()
    parts_dir = parts_dir.strip()
    head_name = head_name.strip() if head_name else None
    dns_name = dns_name.strip() if dns_name else None
    sniffer_name = sniffer_name.strip() if sniffer_name else None
    strategy_name = strategy_name.strip()
    rules_name = rules_name.strip()

    # 必填项校验
    if not template_name:
        raise ValueError("template_name 不能为空。")
    
    if not strategy_name or strategy_name.lower() == 'none':
        raise ValueError("strategy_name 必须填写且不能为空或 none。")
        
    if not rules_name or rules_name.lower() == 'none':
        raise ValueError("rules_name 必须填写且不能为空或 none。")

    if not os.path.exists(parts_dir):
        raise FileNotFoundError(f"文件夹路径 '{parts_dir}' 不存在。")

    # 2. 定义片段及其前缀
    # 按照顺序排列：head -> dns -> sniffer -> strategy -> rules
    parts_config = [
        ('headpart_', head_name),
        ('dnspart_', dns_name),
        ('snifferpart_', sniffer_name),
        ('strategypart_', strategy_name),
        ('rulespart_', rules_name)
    ]

    found_files = []
    
    # 3. 检索文件并校验
    for prefix, name in parts_config:
        if not name or name.lower() == 'none':
            found_files.append(None)
            continue
            
        filename = f"{prefix}{name}.yaml"
        filepath = os.path.join(parts_dir, filename)
        
        if os.path.isfile(filepath):
            found_files.append(filepath)
        else:
            raise FileNotFoundError(f"未找到片段文件 '{filename}'。")

    # 统计有效片段数量
    valid_parts_count = len([f for f in found_files if f is not None])
    if valid_parts_count < 2:
        raise ValueError(f"找到的有效片段数量为 {valid_parts_count}，合并至少需要 2 个片段。")

    # 4. 执行拼接
    parent_dir = os.path.dirname(os.path.abspath(parts_dir))
    output_path = os.path.join(parent_dir, f"{template_name}.yaml")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for i, filepath in enumerate(found_files):
            if filepath is None:
                continue
            
            prefix = parts_config[i][0]
            
            # 在 strategypart 之前插入注释
            if prefix == 'strategypart_':
                outfile.write('# 这里插入节点信息\n')
            
            with open(filepath, 'r', encoding='utf-8') as infile:
                for line in infile:
                    stripped = line.strip()
                    # 去除空行和注释行
                    if not stripped or stripped.startswith('#'):
                        continue
                    outfile.write(line.rstrip() + '\n')
        
    print(f"成功: 模板已生成并保存至 '{output_path}'")
    return output_path

if __name__ == "__main__":
    name = "default_template"
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(current_dir)
    parts_dir = os.path.join(project_root, 'Custom_templates', 'Parts')
    head_name = "default"
    dns_name = "default"
    sniffer_name = "default"
    strategy_name = "default"
    rules_name = "default"
    merge_template(name, parts_dir, head_name, dns_name, sniffer_name, strategy_name, rules_name)
