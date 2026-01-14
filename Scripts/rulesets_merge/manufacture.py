import os
import sys

# 确保脚本可以导入同级目录下的工具模块
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from rulesets_merge_tools import parse_rulesets_yaml, merge_and_save_rulesets

def run_manufacture(config_path):
    """
    主控流程：
    1. 解析主配置
    2. 自动检索同级 Supply_ 文件夹
    3. 调用合并保存工具
    """
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在。")
        return

    # 1. 解析主配置文件
    print(f"\n>>> 步骤 1: 解析主配置文件 {os.path.basename(config_path)}")
    parsed_main = parse_rulesets_yaml(config_path)
    if not parsed_main:
        print("未发现有效规则组，停止。")
        return

    # 2. 自动检索同级目录中以 Supply_ 开头的目录
    src_dir = os.path.dirname(config_path)
    supply_folders = [
        os.path.join(src_dir, d) 
        for d in os.listdir(src_dir) 
        if os.path.isdir(os.path.join(src_dir, d)) and d.startswith('Supply_')
    ]
    
    # 目前 merge_and_save_rulesets 仅支持传入单个路径，我们传入第一个发现的有效路径
    # 如果有多个，可以在此处扩展循环，但通常结构为单补丁库。
    supply_folder = supply_folders[0] if supply_folders else None
    if supply_folder:
        print(f">>> 发现补丁目录: {os.path.basename(supply_folder)}")
    else:
        print(">>> 未发现以 Supply_ 开头的补丁目录，将仅处理主配置规则。")

    # 3. 确定最终输出目录（项目根目录下的 Generated_rulesets）
    # 假设 Scripts 文件夹位于项目根目录下
    project_root = os.path.dirname(current_dir)
    output_dir = os.path.join(project_root, 'Generated_rulesets')

    print(f"\n>>> 步骤 2: 开始执行合并与转换 (输出至: {os.path.relpath(output_dir, project_root)})")
    merge_and_save_rulesets(parsed_main, supply_folder, output_dir)

if __name__ == "__main__":
    # 默认路径：项目根目录/SRC_rulesets/rulesets_src.yaml
    project_root = os.path.dirname(current_dir)
    default_config = os.path.join(project_root, 'SRC_rulesets', 'rulesets_src.yaml')
    
    # 允许从命令行传入路径，否则使用默认
    target_config = sys.argv[1] if len(sys.argv) > 1 else default_config
    
    run_manufacture(target_config)
