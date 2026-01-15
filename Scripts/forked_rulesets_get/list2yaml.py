import os
import sys
import datetime
import yaml
from urllib.parse import urlparse

# 尝试导入 requests
try:
    import requests
except ImportError:
    requests = None
    print("Warning: 'requests' library not found. URL downloading might be limited or fail. Please install it via 'pip install requests'.")

def download_content(url):
    """下载 URL 内容并返回行列表"""
    if requests is None:
        print(f"[Error] 'requests' library is required to download: {url}")
        return []
    
    try:
        print(f"[*] Downloading: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text.splitlines()
    except Exception as e:
        print(f"[Error] Failed to download {url}: {e}")
        return []

def filter_content(content_lines):
    """过滤内容：去除注释、空行等"""
    valid_payloads = []
    for line in content_lines:
        line = line.strip()
        if not line or line.startswith(('#', '//')) or line in ('*', '+'):
            continue
        valid_payloads.append(line)
    return valid_payloads

def save_to_yaml(name, rule_type, payloads, output_dir):
    """将过滤后的内容保存为 Clash YAML 格式"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, f"{name}.yaml")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Generated: {current_time}\n")
            f.write(f"# Type: {rule_type}\n")
            f.write("payload:\n")
            for payload in payloads:
                # 按照用户要求：两个空格缩进，'- '前缀
                f.write(f"  - '{payload}'\n")
        print(f"[Success] Saved: {output_path} ({len(payloads)} rules)")
    except Exception as e:
        print(f"[Error] Failed to save {output_path}: {e}")

def process_rulesets_yaml(input_yaml_path):
    """解析输入的 YAML 配置文件并批量处理规则集"""
    if not os.path.exists(input_yaml_path):
        print(f"[Error] Config file not found: {input_yaml_path}")
        return

    try:
        with open(input_yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"[Error] Failed to parse YAML config: {e}")
        return

    if not config or not isinstance(config, dict):
        print("[Error] Invalid config format.")
        return

    # 输出目录为配置文件同级目录下的 Converted_rulesets
    output_dir = os.path.join(os.path.dirname(input_yaml_path), 'Converted_rulesets')

    for title, info in config.items():
        # 数据校验：title、name、type、url 缺一不可
        name = info.get('name')
        rule_type = info.get('type')
        url = info.get('url')

        if not all([title, name, rule_type, url]):
            print(f"[Skip] Missing required fields in '{title}'.")
            continue

        # 校验 type：只能是 domain 或 ipcidr
        if rule_type not in ['domain', 'ipcidr']:
            print(f"[Skip] Invalid type '{rule_type}' in '{title}'. (Must be domain/ipcidr)")
            continue

        # 处理
        print(f"[*] Processing ruleset: {name} ({rule_type})")
        lines = download_content(url)
        payloads = filter_content(lines)
        
        if payloads:
            save_to_yaml(name, rule_type, payloads, output_dir)
        else:
            print(f"[Warning] No valid rules found for {name}.")

if __name__ == "__main__":
    # 获取项目路径
    current_script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(current_script_path)
    
    # 默认寻找 SRC_rulesets/Forked_rulesets/forked_rulesets.yaml
    # 假设目录结构: Scripts/forked_rulesets_get/list2yaml.py
    # 配置文件在: SRC_rulesets/Forked_rulesets/forked_rulesets.yaml
    project_root = os.path.dirname(os.path.dirname(script_dir))
    default_config = os.path.join(project_root, 'SRC_rulesets', 'Forked_rulesets', 'forked_rulesets.yaml')

    target_config = sys.argv[1] if len(sys.argv) > 1 else default_config
    
    print(f"[*] Starting process with config: {target_config}")
    process_rulesets_yaml(target_config)
