#!/usr/bin/env python3
"""
更新 KVideo 数据源配置
从远程 JSON 获取 api_site 资源，转换为 kvideo.json 格式
"""

import json
import os
import sys
import subprocess
from typing import Dict, Any, List, Tuple

def get_beijing_time() -> dict:
    """获取当前北京时间"""
    result = subprocess.run(
        ["bash", "-c", "TZ='Asia/Shanghai' date +'%Y %m %d %Y-%m-%d %H:%M:%S'"],
        capture_output=True,
        text=True
    )
    parts = result.stdout.strip().split()
    return {
        'YEAR': parts[0],
        'MONTH': parts[1],
        'DAY': parts[2],
        'DATE': parts[3],
        'TIME': parts[4]
    }

def fetch_remote_json(url: str) -> Tuple[bool, Any, str]:
    """从远程获取 JSON 数据"""
    try:
        result = subprocess.run(
            ["bash", "-c", f"curl -sL '{url}'"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return True, data, ""
        return False, None, f"获取失败，退出码: {result.returncode}"
    except json.JSONDecodeError as e:
        return False, None, f"JSON解析失败: {e}"
    except Exception as e:
        return False, None, f"获取异常: {e}"

def convert_source(site_id: str, site_data: Dict[str, Any], priority: int) -> Dict[str, Any]:
    """将远程格式转换为 kvideo.json 格式"""
    return {
        "id": site_id,
        "name": site_data.get("name", ""),
        "baseUrl": site_data.get("api", ""),
        "searchPath": "",
        "detailPath": "",
        "enabled": True,
        "priority": priority
    }

def load_existing_json(file_path: str) -> Tuple[bool, List[Dict], str]:
    """加载现有的 kvideo.json 文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return True, data, ""
                return False, [], f"文件格式错误，根元素不是数组"
        return True, [], ""
    except json.JSONDecodeError as e:
        return False, [], f"JSON解析失败: {e}"
    except Exception as e:
        return False, [], f"读取文件异常: {e}"

def save_json(file_path: str, data: List[Dict]) -> Tuple[bool, str]:
    """保存 JSON 文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=6)
            f.write('\n')
        return True, ""
    except Exception as e:
        return False, f"保存文件异常: {e}"

def git_has_changes(file_path: str) -> bool:
    """检查文件是否有变更"""
    result = subprocess.run(
        ["git", "diff", "--quiet", file_path],
        capture_output=True
    )
    return result.returncode != 0

def main():
    remote_url = "https://raw.githubusercontent.com/hafrey1/LunaTV-config/refs/heads/main/jingjian.json"
    local_file = "KVideo/kvideo.json"
    
    print(f"开始更新 KVideo 数据源...")
    print(f"远程地址: {remote_url}")
    print(f"本地文件: {local_file}")
    
    # 获取远程数据
    print("正在获取远程数据...")
    success, remote_data, error = fetch_remote_json(remote_url)
    if not success:
        print(f"获取远程数据失败: {error}")
        return 1
    
    # 检查是否有 api_site
    if "api_site" not in remote_data:
        print("远程数据中未找到 api_site 字段")
        return 1
    
    api_site = remote_data["api_site"]
    print(f"获取到 {len(api_site)} 个数据源")
    
    # 加载现有数据用于比较
    success, existing_sources, error = load_existing_json(local_file)
    if not success:
        print(f"加载现有数据失败: {error}")
        return 1
    
    # 创建现有资源的 ID 集合用于检查
    existing_ids = {src.get("id") for src in existing_sources}
    
    # 转换远程数据
    new_sources = []
    priority = 1
    added_count = 0
    updated_count = 0
    
    for site_id, site_data in api_site.items():
        source = convert_source(site_id, site_data, priority)
        new_sources.append(source)
        
        # 检查是新添加还是更新
        if site_id in existing_ids:
            updated_count += 1
        else:
            added_count += 1
        
        priority += 1
    
    print(f"转换完成: 新增 {added_count} 个, 更新 {updated_count} 个")
    
    # 保存新数据
    success, error = save_json(local_file, new_sources)
    if not success:
        print(f"保存文件失败: {error}")
        return 1
    
    # 检查是否有变更
    if git_has_changes(local_file):
        print(f"文件已更新: {local_file}")
        
        # 添加到暂存区
        subprocess.run(["git", "add", local_file], check=True)
        
        # 获取北京时间
        time_info = get_beijing_time()
        current_date = f"{time_info['DATE']} {time_info['TIME']}"
        
        # 提交
        subprocess.run([
            "git", "-c", "user.name=GitHub Actions",
            "-c", "user.email=actions@github.com",
            "commit", "-m",
            f"自动更新KVideo数据源 at {current_date}"
        ], check=True)
        
        # 推送
        subprocess.run(["git", "push"], check=True)
        
        print(f"提交并推送成功")
    else:
        print("文件无变更，无需更新")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
