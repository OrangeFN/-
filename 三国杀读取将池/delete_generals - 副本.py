import json
import os
import hashlib

# 精准指向您的项目数据库
base_dir = "D:/pycharm/sgs-2/sgsapp1.0"
js_file = os.path.join(base_dir, "generals_data.js")

# ================= ☠️ 死神点名册 =================
KILL_LIST = [
    "1V1", "巅峰", "国战", "朱雀", "玄武", "青龙", "机雷白虎",
    "守卫剑阁", "吞天螭吻", "魑", "魅", "魍", "魉",
    "浴火士元", "灾煞星", "裂石睚眦", "无常", "劫煞星",
    "绝尘妙才", "巧魁儁义", "食火狻猊", "天候孔明", "天煞星",
    "夜叉", "佳人子丹", "缚地狴犴", "断狱仲达",
]
# ====================================================

if not os.path.exists(js_file):
    print(f"❌ 找不到数据库文件: {js_file}")
    exit()

print("正在读取您的终极数据库...")
with open(js_file, 'r', encoding='utf-8') as f:
    content = f.read()

json_str = content.replace("const ALL_MERGED_GENERALS = ", "").rstrip(";")
data = json.loads(json_str)

deleted_images_count = 0
deleted_by_name = 0
deleted_by_duplicate = 0


def destroy_image(g_data):
    """物理销毁图片辅助函数"""
    global deleted_images_count
    img_rel_path = g_data.get('local_img_path', '')
    if img_rel_path:
        img_abs_path = os.path.join(base_dir, img_rel_path)
        if os.path.exists(img_abs_path):
            try:
                os.remove(img_abs_path)
                deleted_images_count += 1
                print(f"      🗑️ 连带销毁原画: {os.path.basename(img_abs_path)}")
            except Exception as e:
                print(f"      ⚠️ 图片删除失败: {e}")


def get_skill_hash(skills_list):
    """技能极高精度摘要算法"""
    sorted_skills = sorted(skills_list, key=lambda x: x.get('name', ''))
    skills_str = json.dumps(sorted_skills, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(skills_str.encode('utf-8')).hexdigest()


def get_server_priority(server_name):
    """定义服务器保留优先级：数字越小，优先级越高"""
    if "十周年" in server_name:
        return 1
    elif "ol" in server_name.lower():
        return 2
    else:
        return 3  # 其他版本垫底


# ================= ⚔️ 第一阶段：黑名单斩杀 =================
phase1_survivors = []
for g in data:
    if any(bad_name in g['name'] for bad_name in KILL_LIST):
        print(f"  🔪 斩杀黑名单武将: {g['name']} ({g['server']})")
        destroy_image(g)
        deleted_by_name += 1
    else:
        phase1_survivors.append(g)

# ================= ⚔️ 第二阶段：同技能打擂台 =================
skill_groups = {}
zero_skill_generals = []

# 1. 按照技能哈希值进行分组
for g in phase1_survivors:
    skills = g.get('skills', [])
    if len(skills) == 0:
        # 0 技能的武将不参与内卷，直接保送存活
        zero_skill_generals.append(g)
    else:
        s_hash = get_skill_hash(skills)
        if s_hash not in skill_groups:
            skill_groups[s_hash] = []
        skill_groups[s_hash].append(g)

# 2. 在每个组内部按优先级“大逃杀”
final_survivors = []
final_survivors.extend(zero_skill_generals)

for s_hash, group in skill_groups.items():
    if len(group) == 1:
        # 独一无二的武将，直接存活
        final_survivors.append(group[0])
    else:
        # 出现了重复！按照我们定义的优先级（1 > 2 > 3）进行排序
        sorted_group = sorted(group, key=lambda x: get_server_priority(x.get('server', '')))

        # 排名第一的胜出保留
        winner = sorted_group[0]
        final_survivors.append(winner)

        # 剩下的全部处决
        for loser in sorted_group[1:]:
            print(f"  👯 移除重复武将: {loser['name']} ({loser['server']}) 👉 优先保留了: {winner['server']} 版本")
            destroy_image(loser)
            deleted_by_duplicate += 1

# ================= ⚔️ 第三阶段：重新封写入库 =================
print(f"\n正在将存活的 {len(final_survivors)} 名武将重新封写入库...")
with open(js_file, 'w', encoding='utf-8') as f:
    f.write("const ALL_MERGED_GENERALS = ")
    json.dump(final_survivors, f, ensure_ascii=True)
    f.write(";")

print(f"\n🎉 终极大清洗与【优先级去重】完成！")
print(f"☠️ 共计抹除 {deleted_by_name + deleted_by_duplicate} 个武将！")
print(f"   - 因【黑名单】斩杀: {deleted_by_name} 名")
print(f"   - 因【技能重复】淘汰: {deleted_by_duplicate} 名")
print(f"💥 硬盘空间释放：共物理销毁了 {deleted_images_count} 张废弃原画！")