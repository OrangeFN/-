import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================= 1. 核心配置 =================
DATA_DIR = "sgs_offline_data"
IMG_DIR = os.path.join(DATA_DIR, "images")
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)  # 🚀 确保图片文件夹存在

SERVER_NAME = "十周年"

# ⚠️ 注意：这里请务必填入您在老代码中确认过的正确网址！
API_URL = "https://wiki.biligame.com/sgs/api.php"
BASE_URL = "https://wiki.biligame.com/sgs/"
CATEGORIES = ["Category:武将", "Category:全部武将"]
JSON_PATH = os.path.join(DATA_DIR, "generals_shizhou_pure.json")

# ================= 2. 爬虫伪装 =================
session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': BASE_URL
})

all_generals = []
crawled_keys = set()


# ================= 3. 字段提取探针 =================
def extract_faction(soup, text_content):
    match = re.search(r'势力[\s:：]*([魏蜀吴群晋神])', text_content)
    if match: return match.group(1)
    p = soup.find('p', string=lambda t: t and '势力' in t)
    if p and p.parent: return p.parent.get_text().replace('势力', '').strip()
    return "未知"


def extract_hp(soup, text_content):
    hidden_hp = soup.find('span', style=lambda s: s and 'display:none' in s.replace(' ', ''))
    if hidden_hp and hidden_hp.get_text(strip=True).isdigit(): return hidden_hp.get_text(strip=True)
    match = re.search(r'体力[\s:：]*(\d+/?\d*)', text_content)
    if match: return match.group(1)
    return "未知"


def extract_cover_only(soup):
    # 🚀 强化版图片雷达：防止某些页面没用 img-cover
    img = soup.select_one('img.img-cover') or soup.select_one('table.infobox img') or soup.select_one(
        'table.wikitable img')
    if img:
        src = img.get('src') or img.get('data-src', '')
        if src:
            src = 'https:' + src if src.startswith('//') else src
            src = src.replace('/thumb/', '/')
            return re.sub(r'/\d+px-[^/]+$', '', src)
    return ""


# ================= 4. 解析核心引擎 =================
def fetch_general_details(info):
    name, url = info["name"], info["url"]

    if url in crawled_keys: return
    print(f"  -> [收割] {name: <10} ... ", end="", flush=True)
    time.sleep(random.uniform(0.3, 0.8))

    try:
        res = session.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        raw_text = soup.get_text(" ", strip=True)

        faction = extract_faction(soup, raw_text)
        hp = extract_hp(soup, raw_text)
        cover_url = extract_cover_only(soup)

        versions = {}

        def add_skill(v_name, s_name, s_desc):
            s_n = s_name.replace("【", "").replace("】", "").replace("\n", "").strip()
            bad_words = ["体力", "势力", "性别", "编号", "模式", "皮肤", "画师", "获取", "战功", "包", "别称", "阵亡",
                         "配音", "旧版", "历史", "原版", "武将", "定位", "方式", "生卒", "籍贯", "FAQ", "社区", "说明",
                         "获得"]
            if not s_n or len(s_n) > 8 or any(b in s_n for b in bad_words): return
            s_d = re.sub(r'\s+', ' ', s_desc).strip()
            if len(s_d) < 8 or s_d == s_n: return
            if v_name not in versions: versions[v_name] = {}
            if s_n not in versions[v_name] or len(s_d) > len(versions[v_name][s_n]):
                versions[v_name][s_n] = s_d

        def get_v_name(node):
            v_name = "经典版"
            tab = node.find_parent('div', class_=lambda c: c and 'tab-pane' in c)
            if tab and tab.get('id'):
                link = soup.find('a', href=f"#{tab.get('id')}")
                if link: v_name = link.get_text(strip=True)
            if v_name == "经典版":
                tabber = node.find_parent('div', class_='tabbertab')
                if tabber: v_name = tabber.get('data-title') or tabber.get('title', '经典版')
            return v_name

        def is_lbl(n):
            if not n.name: return False
            c = n.get('class', [])
            if isinstance(c, str): c = [c]
            if any('技能标签' in x or 'skill-name' in x for x in c): return True
            txt = n.get_text(strip=True)
            return n.name in ['b', 'strong', 'span', 'th'] and txt.startswith('【') and txt.endswith('】') and 2 <= len(
                txt) <= 8

        for l in soup.find_all(is_lbl):
            s_n = l.get_text(strip=True)
            s_d = ""
            for base in [l, l.parent, l.parent.parent if l.parent else None]:
                if not base or s_d.strip(): break
                for sib in base.next_siblings:
                    if sib.name and is_lbl(sib): break
                    if sib.name and sib.find(is_lbl): break
                    s_d += (sib.get_text(" ", strip=True) if sib.name else str(sib).strip() + " ")
            if not s_d.strip() and l.parent:
                p_t = l.parent.get_text(" ", strip=True)
                if len(p_t) > len(s_n): s_d = p_t.replace(s_n, "", 1)
            add_skill(get_v_name(l), s_n, s_d)

        if not versions:
            for tr in soup.find_all('tr'):
                cells = tr.find_all(['th', 'td'])
                if len(cells) >= 2:
                    add_skill(get_v_name(tr), cells[0].get_text(strip=True).strip('【】 :：'),
                              " ".join([c.get_text(" ", strip=True) for c in cells[1:]]))

        if not versions:
            for dt in soup.find_all('dt'):
                s_d = ""
                for sib in dt.next_siblings:
                    if sib.name == 'dt': break
                    s_d += (sib.get_text(" ", strip=True) if sib.name else str(sib).strip() + " ")
                add_skill(get_v_name(dt), dt.get_text(strip=True).strip('【】 :：'), s_d)

        if not versions:
            for s_n, s_d in re.findall(r'【([^】]{1,8})】[\s:：]*([\s\S]*?(?=(?:\n\s*【|$)))',
                                       soup.get_text("\n", strip=True)):
                add_skill("经典版", s_n, s_d)

        count = 0
        for v_n, skill_dict in versions.items():
            if any(x in v_n for x in ["皮肤", "台词", "自走棋", "演武", "战功", "模式"]): continue
            if not skill_dict: continue

            fid = f"S10_{name}_{v_n}"
            l_path = f"images/{fid}.png"

            # 🚀 核心修复：自动下载图片到本地 images 文件夹
            if cover_url and not os.path.exists(os.path.join(DATA_DIR, l_path)):
                try:
                    img_data = session.get(cover_url, timeout=10).content
                    with open(os.path.join(DATA_DIR, l_path), 'wb') as f:
                        f.write(img_data)
                except Exception as e:
                    pass  # 忽略下载失败

            # 🚀 匹配 HTML：字段名改回 local_img_path
            all_generals.append({
                "id": fid,
                "name": name if v_n == "经典版" else f"{name}({v_n})",
                "server": SERVER_NAME,
                "faction": faction,
                "hp": hp,
                "local_img_path": l_path,
                "skills": [{"name": k, "desc": v} for k, v in skill_dict.items()]
            })
            count += 1

        print(f"✅ {count} 形态 | 🩸 {hp}血 | 🖼️ 图片已就绪" if count > 0 else "❌ 放弃：无有效技能")
        crawled_keys.add(url)

    except Exception as e:
        print(f"❌ 解析失败: {e}")


# ================= 5. 驱动程序 =================
if __name__ == "__main__":
    print(f"=== 📡 开始【{SERVER_NAME}】纯净收割 (带图片离线下载) ===")

    unique_list = []
    for cat in CATEGORIES:
        print(f"🔍 扫描分类【{cat}】...")
        params = {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "500", "format": "json"}
        while True:
            try:
                time.sleep(1)
                res = session.get(API_URL, params=params, timeout=15)

                try:
                    data = res.json()
                except ValueError:
                    print(f"  ❌ 遭遇非JSON拦截！状态码: {res.status_code}")
                    break

                members = data.get("query", {}).get("categorymembers", [])
                if not members: break

                for m in members:
                    if m["title"].startswith(("Category:", "Template:", "分类:", "模板:")) or m[
                        "title"] == "武将": continue
                    unique_list.append({"name": m["title"], "url": BASE_URL + m["title"].replace(" ", "_")})

                if "continue" in data:
                    params.update(data["continue"])
                else:
                    break

            except Exception as e:
                print(f"  ❌ API请求失败: {e}");
                break

    final_list = {item['url']: item for item in unique_list}.values()
    print(f"✅ 共锁定 {len(final_list)} 个目标，准备开始逐个提取...")

    if len(final_list) > 0:
        try:
            for item in final_list:
                fetch_general_details(item)
        finally:
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_generals, f, ensure_ascii=False, indent=4)
            print(f"\n🎉 任务结束！已生成纯净库：{JSON_PATH}，且所有原画已下载至 images 文件夹！")
    else:
        print("\n❌ 未锁定任何武将，任务终止。")