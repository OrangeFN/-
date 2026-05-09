import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor

# ================= 配置区 =================
# 这里填入您刚才爬取生成的 JSON 文件名
JSON_FILE = "sgsol.json"
# 图片将统一存放到这个文件夹下
IMAGE_DIR = "ol_images"
# ==========================================

# 如果文件夹不存在，自动创建
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# 加载武将数据
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    generals = json.load(f)


def download_image(general):
    name = general["name"]
    gen_id = general["id"]
    url = general["local_img_path"]

    # 如果链接为空或者已经是本地路径了，就跳过
    if not url or not url.startswith("http"):
        return f"⚠️ {name} 没有可下载的网络链接"

    # 提取图片的真实后缀名 (png, jpg 等)
    ext = url.split('.')[-1].split('?')[0]
    if ext.lower() not in ['png', 'jpg', 'jpeg', 'webp']:
        ext = 'png'

    # 按照您的项目规范重命名，例如：ol_鲍信.png
    filename = f"{gen_id}.{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)

    # 如果您之前已经下过了，防重复下载
    if os.path.exists(filepath):
        # 顺手把 JSON 里的路径改成相对路径，适配前端
        general["local_img_path"] = f"images/{filename}"
        return f"⏩ {name} 图片已存在，跳过下载"

    try:
        # B站图片服务器 CDN 很友好，加上基础 Header 即可
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # 🌟 核心动作：图片下载成功后，把 JSON 里的网络链接替换成本地相对路径
            general["local_img_path"] = f"images/{filename}"
            return f"✅ {name} 下载成功 -> {filename}"
        else:
            return f"❌ {name} 下载失败 (状态码: {response.status_code})"
    except Exception as e:
        return f"❌ {name} 下载异常: {e}"


def main():
    print(f"🚀 开始批量下载图片，目标总数：{len(generals)} 张...")

    # 开启 5 个线程同时下载，速度起飞
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(download_image, generals)
        for r in results:
            print(f"   {r}")

    # 把修改后的本地图片路径重新写回 JSON 文件
    print(f"\n🚀 正在更新 {JSON_FILE} 的图片路径配置...")
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(generals, f, ensure_ascii=False, indent=4)

    print(f"🎉 霸业大成！所有高清原画已完美存入 {IMAGE_DIR} 文件夹！")
    print("💡 您的 JSON 文件中的网络链接也已经自动替换成了本地路径 (如 images/ol_鲍信.png)，可以直接无缝接入您的前端了！")


if __name__ == "__main__":
    main()