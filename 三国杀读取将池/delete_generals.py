import json
import os

# 精准指向您的项目数据库
base_dir = "D:/pycharm/sgs-2/sgsapp1.0"
js_file = os.path.join(base_dir, "generals_data.js")

# ================= ☠️ 死神点名册 =================
# 只要武将的名字里【包含】这里的词，就会被无情抹除！
KILL_LIST = [
    "1V1",
    "巅峰",
    "国战",
    "朱雀",
    "玄武",
    "青龙",
    "机雷白虎",
    "守卫剑阁",
    "吞天螭吻",
    "魑",
    "魅",
    "魍",
    "魉",
    "浴火士元",
    "灾煞星",
    "裂石睚眦",
    "无常",
    "劫煞星",
    "绝尘妙才",
    "巧魁儁义",
    "食火狻猊",
    "天候孔明",
    "天煞星",
    "夜叉",
    "佳人子丹",
    "缚地狴犴",
    "断狱仲达",
     # 👈 在这里填入您要抹除的武将
]
# ====================================================

if not os.path.exists(js_file):
    print(f"❌ 找不到数据库文件: {js_file}")
    exit()

print("正在读取您的终极数据库...")
with open(js_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 剥离外壳，提取纯 JSON 数据
json_str = content.replace("const ALL_MERGED_GENERALS = ", "").rstrip(";")
data = json.loads(json_str)

original_count = len(data)
survivors = []
deleted_images_count = 0

print(f"开始执行大清洗，目标名单：{KILL_LIST}")

# 🚀 核心过滤与物理销毁引擎
for g in data:
    # 检查这个武将的名字是否在黑名单里
    is_target = any(bad_name in g['name'] for bad_name in KILL_LIST)

    if not is_target:
        survivors.append(g)
    else:
        print(f"  🔪 斩杀武将: {g['name']} ({g['server']})")

        # 🚀 新增大招：顺藤摸瓜，物理销毁对应的乱码图片文件
        img_rel_path = g.get('local_img_path', '')
        if img_rel_path:
            # 拼接出图片在电脑上的绝对路径
            img_abs_path = os.path.join(base_dir, img_rel_path)

            # 如果图片存在硬盘里，直接物理删除
            if os.path.exists(img_abs_path):
                try:
                    os.remove(img_abs_path)
                    deleted_images_count += 1
                    print(f"      🗑️ 连带销毁原画: {os.path.basename(img_abs_path)}")
                except Exception as e:
                    print(f"      ⚠️ 图片删除失败，可能已被占用或删除: {e}")

deleted_count = original_count - len(survivors)

print(f"\n正在将存活的 {len(survivors)} 名武将重新封写入库...")
with open(js_file, 'w', encoding='utf-8') as f:
    f.write("const ALL_MERGED_GENERALS = ")
    # 保持 ensure_ascii=True 确保安卓绝对安全兼容
    json.dump(survivors, f, ensure_ascii=True)
    f.write(";")

print(f"\n🎉 终极大清洗完成！")
print(f"☠️ 共从数据库抹除了 {deleted_count} 个武将，并在硬盘上物理销毁了 {deleted_images_count} 张原画图片！")