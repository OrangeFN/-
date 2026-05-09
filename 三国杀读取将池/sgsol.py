import requests
import json
import time
import random
import re
from bs4 import BeautifulSoup

# ================= 配置区 =================
API_URL = "https://wiki.biligame.com/sgsol/api.php"
SAVE_FILE = "sgsol.json"
TEST_LIMIT = None  # 试水模式，抓前 50 个
# ==========================================

session = requests.Session()
headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://wiki.biligame.com/sgsol/"}


def get_roster():
    print("🚀 [阶段 1/3] 正在拉取武将名单...")
    all_gen = []
    params = {"action": "query", "list": "categorymembers", "cmtitle": "Category:武将", "cmlimit": "500",
              "format": "json"}

    while True:
        try:
            # 🛡️ 修复点：在每次请求名单前强制休眠，防止翻页时被瞬间狙击拦截
            time.sleep(1.5)

            resp = session.get(API_URL, params=params, headers=headers).json()
            members = resp.get("query", {}).get("categorymembers", [])
            for m in members:
                if ":" not in m["title"]:
                    all_gen.append(m["title"])

            # 翻页逻辑
            if "continue" in resp:
                params["cmcontinue"] = resp["continue"]["cmcontinue"]
                print(f"   ▶️ 触发翻页，当前已获取 {len(all_gen)} 名，继续潜行拉取...")
            else:
                break

        except Exception as e:
            # 🛡️ 修复点：不再静默吞错，如实暴露拦截原因
            print(f"⚠️ 拉取名单时报错被拦截: {e}")
            break

    print(f"✅ Wiki 总共有 {len(all_gen)} 名武将。")
    if TEST_LIMIT:
        all_gen = all_gen[:TEST_LIMIT]
        print(f"🎯 测试模式：只抓取前 {TEST_LIMIT} 名！")
    return all_gen


# 🧠 强力脱水机 V2：精准过滤所有乱码、单字和 UI 噪音
def clean_skill_name(raw_name, general_name):
    # 1. 基础清理
    s = str(raw_name).replace("【", "").replace("】", "").replace("：", "").replace(":", "")
    s = s.replace("，", "").replace(",", "").replace("。", "")
    # 🌟 杀手锏：彻底消灭幽灵空格 \xa0 和普通空格
    s = s.replace('\xa0', '').replace('\u3000', '').replace(' ', '')

    # 2. 剥离武将名和体力数字
    s = s.replace(general_name, "")
    s = re.sub(r'\d+', '', s).strip()

    # 3. 剥离技能前缀词 (注意：必须先 strip 再判断，防止前面有暗藏的空格)
    prefixes = ["锁定技", "限定技", "觉醒技", "转换技", "主公技", "阵法技", "隐匿技", "使命技", "宗族技", "附加技"]
    for p in prefixes:
        if s.startswith(p):
            s = s[len(p):].strip()

    # 4. 彻底枪毙黑名单 (把您截图里的那些 UI 词全加进去了)
    bad_exact = ["技能", "武将技能", "台词", "武将台词", "人物生平", "皮肤", "其它", "其他", "连环状态", "经典形象",
                 "出牌阶段", "结束阶段", "说明", "阵亡"]

    # 🌟 杀手锏 2：三国杀没有 1个字的技能！直接干掉 '书'、'傀' 等标记词！
    if s in bad_exact or len(s) < 2 or len(s) > 6:
        return ""

    # 如果包含句式词，说明抓到了一整句话，直接抛弃
    if any(x in s for x in ["的", "了", "在", "是", "你可以"]):
        return ""

    return str(s)


def parse_general_data(name):
    result = {"id": f"ol_{name}", "name": str(name), "server": "ol", "faction": "未知", "hp": "3", "local_img_path": "",
              "skills": []}
    params = {"action": "parse", "page": name, "prop": "text|wikitext|images", "format": "json"}

    try:
        time.sleep(random.uniform(0.8, 1.5))
        resp = session.get(API_URL, params=params, headers=headers, timeout=15).json()
        if "parse" not in resp: return result

        parse_data = resp["parse"]
        html = parse_data.get("text", {}).get("*", "")
        wikitext = parse_data.get("wikitext", {}).get("*", "")
        images = parse_data.get("images", [])

        # ==========================================
        # 1. 🩸 底层提取势力与体力
        # ==========================================
        f_match = re.search(r'\|\s*势力\s*=\s*([魏蜀吴群晋神])', wikitext)
        if f_match: result["faction"] = str(f_match.group(1))

        hp_match = re.search(r'\|\s*(?:经典)?(?:体力|血量)\s*=\s*(\d+)', wikitext)
        if hp_match: result["hp"] = str(hp_match.group(1))

        # ==========================================
        # 2. 🖼️ API 官方图库直提原画
        # ==========================================
        target_img = ""
        for img in images:
            if "经典形象" in img or "原画" in img:
                target_img = img;
                break
        if not target_img:
            for img in images:
                if name in img and not any(k in img.lower() for k in ["头像", "勾玉", "图标", "logo"]):
                    target_img = img;
                    break

        if target_img:
            img_params = {"action": "query", "titles": f"File:{target_img}", "prop": "imageinfo", "iiprop": "url",
                          "format": "json"}
            img_data = session.get(API_URL, params=img_params, headers=headers).json()
            pages = img_data.get("query", {}).get("pages", {})
            for pid, info in pages.items():
                if "imageinfo" in info:
                    result["local_img_path"] = str(info["imageinfo"][0]["url"])
                    break

        # ==========================================
        # 3. 🎯 技能提取
        # ==========================================
        soup = BeautifulSoup(html, 'html.parser')
        skills_dict = {}

        for tag in soup.find_all(['b', 'strong', 'dt', 'span', 'div']):
            is_valid = False
            if tag.name == 'dt':
                is_valid = True
            elif tag.has_attr('class') and any(
                    c in tag['class'] for c in ['bold-font', 'tooltip-label-container', 'mw-headline']):
                is_valid = True
            elif tag.name in ['b', 'strong'] and (
                    tag.find_parent('div', class_='tooltip-content') or tag.find_parent('dl')):
                is_valid = True

            if not is_valid: continue

            raw_text = tag.get_text(strip=True)
            c_name = clean_skill_name(raw_text, name)
            if not c_name: continue  # 如果被净水器过滤掉了，直接跳过

            desc = ""
            if tag.name == 'dt':
                nxt = tag.find_next_sibling('dd')
                if nxt: desc = nxt.get_text(separator="", strip=True)
            else:
                parent = tag.parent
                if parent:
                    full_p = parent.get_text(separator="", strip=True)
                    parts = full_p.split(raw_text, 1)
                    if len(parts) > 1:
                        desc = parts[1]
                    else:
                        nxt = parent.find_next_sibling()
                        if nxt: desc = nxt.get_text(separator="", strip=True)

            desc = desc.replace(name, "")
            desc = re.sub(r'^\s*\d+\s*', '', desc).strip(" ：:，,")

            if len(desc) > 5:
                if c_name not in skills_dict or len(desc) > len(skills_dict[c_name]):
                    skills_dict[c_name] = str(desc)

        result["skills"] = [{"name": k, "desc": v} for k, v in skills_dict.items()]

    except Exception as e:
        pass

    return result


def main():
    names = get_roster()
    if not names: return

    final_data = []
    print(f"\n🚀 [阶段 2/3] 启动【底层溯源 + 强力清洗 V2】...\n")

    for i, name in enumerate(names, 1):
        res = parse_general_data(name)
        final_data.append(res)

        s_names = [s['name'] for s in res['skills']]
        img_flag = "✅" if res['local_img_path'] else "❌"
        print(
            f"   ⏳ {i}/{len(names)} | {res['name']} ({res['faction']}-{res['hp']}血) | 技能: {len(s_names)}个 {s_names} | 图片: {img_flag}")

    print(f"\n🚀 [阶段 3/3] 写入本地文件...")
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"🎉 搞定！这回全是干干净净的真技能！跑完全服直接起飞！")


if __name__ == "__main__":
    main()