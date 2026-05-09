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
DATA_DIR = "msgs_offline_data"
IMG_DIR = os.path.join(DATA_DIR, "images")
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(IMG_DIR): os.makedirs(IMG_DIR)

SERVER_NAME = "移动版"
API_URL = "https://wiki.biligame.com/msgs/api.php"
BASE_URL = "https://wiki.biligame.com/msgs/"
CATEGORIES = ["Category:武将", "Category:全部武将"]
JSON_PATH = os.path.join(DATA_DIR, "generals_mobile_pure.json")

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


# ================= 3. 解析核心引擎 (防碎片化终极版) =================
def fetch_general_details(info):
    name, url = info["name"], info["url"]

    if url in crawled_keys: return
    print(f"  -> [收割] {name: <10} ... ", end="", flush=True)
    time.sleep(random.uniform(0.3, 0.6))

    try:
        res = session.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 🚀 绝招 1：消歧义核弹，彻底粉碎“是一个多义词”的污染
        for alert in soup.find_all('div', class_=lambda c: c and 'alert' in c):
            alert.extract()

        # 🚀 绝招 2：看图说话（把黑桃、红桃、杀的图标翻译成文字，防止断句）
        for img in soup.find_all('img'):
            alt = img.get('alt', '')
            if alt:
                alt_clean = alt.replace('.png', '').replace('.jpg', '')
                if len(alt_clean) <= 4:  # 如 "黑桃", "杀", "魏"
                    img.replace_with(f"[{alt_clean}]")

        # 提取全局势力与血量
        faction = "未知"
        faction_node = soup.find('p', string=re.compile(r'势力'))
        if faction_node and faction_node.parent:
            faction = faction_node.parent.get_text(strip=True).replace('势力', '').strip()

        global_hp = "未知"
        for span in soup.find_all('span', style=lambda s: s and 'display:none' in s.replace(' ', '')):
            txt = span.get_text(strip=True)
            if any(c.isdigit() for c in txt) and len(txt) <= 5:
                global_hp = txt.replace('[@×', '').replace('×', '').replace(']', '')
                break

        versions_found = 0

        # 遍历每一个形态版本 (如 经典、国战)
        for headline in soup.find_all('span', class_='mw-headline'):
            v_name = headline.get_text(strip=True)
            if v_name in ["皮肤", "规则集问答", "词条", "攻略", "台词", "相关推荐", "成就"]: continue

            if not headline.parent or not headline.parent.parent or not headline.parent.parent.parent:
                continue
            wrapper = headline.parent.parent.parent

            skill_section = wrapper.find('div', class_=lambda c: c and 'character-lines-and-skills-section' in c)
            if not skill_section: continue

            skills_data = []
            labels = skill_section.find_all('div', class_=lambda c: c and 'basic-info-row-label' in c)

            # 🚀 绝招 3：连坐收割法 (解决长篇技能被截断的问题)
            for i, label_div in enumerate(labels):
                if label_div.find_parent(class_='histroy-skill'): continue

                s_n = label_div.get_text(strip=True)
                s_n = re.sub(r'[【】\[\]\s:：☆]', '', s_n).strip()

                # 严格的名字过滤
                if not (1 <= len(s_n) <= 6): continue
                if s_n in ["Q", "A", "杀", "闪", "桃", "酒", "阵亡"]: continue
                if "多义词" in s_n or "浏览" in s_n: continue

                parent_div = label_div.parent
                if not parent_div: continue

                # 第一部分：盒子里的文字
                desc_parts = [parent_div.get_text(" ", strip=True).replace(label_div.get_text(" ", strip=True), "", 1)]

                # 第二部分：一路向下收割无家可归的段落，直到碰见下一个技能的盒子
                next_parent = labels[i + 1].parent if i + 1 < len(labels) else None
                curr = parent_div.next_sibling

                while curr and curr != next_parent:
                    # 遇到大标题或“台词”区域立刻刹车
                    if curr.name in ['h2', 'h3', 'h4']: break
                    if curr.name == 'div' and 'middle-grey-side-transparen-bg' in curr.get('class', []): break

                    if curr.name:
                        desc_parts.append(curr.get_text(" ", strip=True))
                    else:
                        txt = str(curr).strip()
                        if txt: desc_parts.append(txt)

                    curr = curr.next_sibling

                # 拼接并清洗
                s_d = " ".join(desc_parts).strip()
                s_d = re.sub(r'\s+', ' ', s_d)

                # 最后一道防线过滤垃圾信息
                if len(s_d) > 5 and not any(kw in s_d for kw in ["词条 +", "暂无攻略", "点击可进行皮肤", "多义词"]):
                    if not any(s['name'] == s_n for s in skills_data):
                        skills_data.append({"name": s_n, "desc": s_d})

            if not skills_data: continue

            # 专属血量与原画
            hp = global_hp
            for span in wrapper.find_all('span', style=lambda s: s and 'display:none' in s.replace(' ', '')):
                txt = span.get_text(strip=True)
                if any(c.isdigit() for c in txt) and len(txt) <= 5:
                    hp = txt.replace('[@×', '').replace('×', '').replace(']', '')
                    break

            cover_url = ""
            img_cover = wrapper.select_one('img.img-cover')
            if img_cover:
                src = img_cover.get('src') or img_cover.get('data-src', '')
                if src:
                    src = 'https:' + src if src.startswith('//') else src
                    src = src.replace('/thumb/', '/')
                    cover_url = re.sub(r'/\d+px-[^/]+$', '', src)

            fid = f"mobile_{name}_{v_name}"
            l_path = f"images/{fid}.png"

            if cover_url and not os.path.exists(os.path.join(DATA_DIR, l_path)):
                try:
                    img_data = session.get(cover_url, timeout=10).content
                    with open(os.path.join(DATA_DIR, l_path), 'wb') as f:
                        f.write(img_data)
                except:
                    pass

            all_generals.append({
                "id": fid,
                "name": name if v_name in ["经典", "经典版"] else f"{name}({v_name})",
                "server": SERVER_NAME,
                "faction": faction,
                "hp": hp,
                "local_img_path": l_path,
                "skills": skills_data
            })
            versions_found += 1

        print(f"✅ {versions_found} 形态 | 🩸 {global_hp}血" if versions_found > 0 else "❌ 放弃：未找到技能")
        crawled_keys.add(url)

    except Exception as e:
        print(f"❌ 解析失败: {e}")


# ================= 4. 驱动程序 =================
if __name__ == "__main__":
    print(f"=== 📡 开始【{SERVER_NAME}】完美收割 (防碎片化终极版) ===")

    unique_list = []
    for cat in CATEGORIES:
        print(f"🔍 扫描分类【{cat}】...")
        params = {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "500", "format": "json"}
        while True:
            try:
                time.sleep(1)
                res = session.get(API_URL, params=params, timeout=15)
                data = res.json()
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
            print(f"\n🎉 任务结束！已生成完美纯净库：{JSON_PATH}。多义词已粉碎，长技能已全部缝合！")
    else:
        print("\n❌ 未锁定任何武将，任务终止。")