#!/usr/bin/env python3
"""
更新 KVideo 和 NextTV 数据源配置
从远程 JSON 获取 api_site 资源，转换为 kvideo.json 和 NextTV/NextTV.json 格式
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

def convert_to_kvideo(site_id: str, site_data: Dict[str, Any], priority: int) -> Dict[str, Any]:
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

def convert_to_nexttv(site_id: str, site_data: Dict[str, Any], item_id: int) -> Dict[str, Any]:
    """将远程格式转换为 NextTV.json 格式"""
    return {
        "id": str(item_id),
        "name": site_data.get("name", ""),
        "key": site_id,
        "url": site_data.get("api", ""),
        "enabled": True,
        "type": "video"
    }

def load_json_file(file_path: str) -> Tuple[bool, Any, str]:
    """加载 JSON 文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return True, data, ""
        return True, None, ""
    except json.JSONDecodeError as e:
        return False, None, f"JSON解析失败: {e}"
    except Exception as e:
        return False, None, f"读取文件异常: {e}"

def save_kvideo_json(file_path: str, data: List[Dict]) -> Tuple[bool, str]:
    """保存 kvideo.json（数组格式）"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=6)
            f.write('\n')
        return True, ""
    except Exception as e:
        return False, f"保存文件异常: {e}"

def save_nexttv_json(file_path: str, data: List[Dict]) -> Tuple[bool, str]:
    """保存 NextTV.json（对象格式）"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"videoSources": data}, f, ensure_ascii=False, indent=2)
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
    
    print(f"开始更新 KVideo 和 NextTV 数据源...")
    print(f"远程地址: {remote_url}")
    
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
    
    # 转换数据
    kvideo_sources = []
    nexttv_sources = []
    priority = 1
    item_id = 1
    
    for site_id, site_data in api_site.items():
        kvideo_sources.append(convert_to_kvideo(site_id, site_data, priority))
        nexttv_sources.append(convert_to_nexttv(site_id, site_data, item_id))
        priority += 1
        item_id += 1
    
    print(f"转换完成: 共 {len(kvideo_sources)} 个数据源")
    
    # 保存 kvideo.json
    kvideo_file = "KVideo/kvideo.json"
    success, error = save_kvideo_json(kvideo_file, kvideo_sources)
    if not success:
        print(f"保存 {kvideo_file} 失败: {error}")
        return 1
    kvideo_changed = git_has_changes(kvideo_file)
    print(f"kvideo.json {'有变更' if kvideo_changed else '无变更'}")
    
    # 保存 NextTV.json
    nexttv_file = "NextTV/NextTV.json"
    success, error = save_nexttv_json(nexttv_file, nexttv_sources)
    if not success:
        print(f"保存 {nexttv_file} 失败: {error}")
        return 1
    nexttv_changed = git_has_changes(nexttv_file)
    print(f"NextTV.json {'有变更' if nexttv_changed else '无变更'}")
    
    # 检查是否有任何变更
    if not kvideo_changed and not nexttv_changed:
        print("所有文件无变更，无需更新")
        return 0
    
    # 添加变更文件到暂存区
    files_to_commit = []
    if kvideo_changed:
        subprocess.run(["git", "add", kvideo_file], check=True)
        files_to_commit.append("kvideo.json")
    if nexttv_changed:
        subprocess.run(["git", "add", nexttv_file], check=True)
        files_to_commit.append("NextTV.json")
    
    # 获取北京时间
    time_info = get_beijing_time()
    current_date = f"{time_info['DATE']} {time_info['TIME']}"
    
    # 提交
    commit_msg = f"自动更新数据源 at {current_date}"
    subprocess.run([
        "git", "-c", "user.name=GitHub Actions",
        "-c", "user.email=actions@github.com",
        "commit", "-m", commit_msg
    ], check=True)
    
    # 推送
    subprocess.run(["git", "push"], check=True)
    
    print(f"提交并推送成功: {', '.join(files_to_commit)}")
    
    # 输出变更状态供 GitHub Actions 使用
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"HAS_CHANGES=true\n")
        f.write(f"FILES_CHANGED={','.join(files_to_commit)}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
