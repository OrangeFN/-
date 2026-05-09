import json
import os

# 1. 指向您 PyCharm 里的三个数据文件夹路径（注意把斜杠换成您的实际路径）
base_dir = "D:/pycharm/sgs-2/sgs0508/"
files = [
    os.path.join(base_dir,  "generals_mobile_pure.json"),
    os.path.join(base_dir,  "generals_shizhou_pure.json"),
    os.path.join(base_dir,  "generals_sgsol_pure.json") # 注意这里是重命名后的名字
]

all_generals = []

for file_name in files:
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_generals.extend(data)
            print(f"✅ 成功读取: {os.path.basename(file_name)} ({len(data)}将)")
    else:
        print(f"❌ 找不到文件: {file_name}")

# 2. 指向您桌面的 App 文件夹路径
# ⚠️ 这里填您桌面上那个 SgsApp 文件夹的绝对路径
output_file = 'D:/pycharm/sgs-2/sgsapp-1/generals_data.js'

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("const ALL_MERGED_GENERALS = ")
    json.dump(all_generals, f, ensure_ascii=False)
    f.write(";")

print(f"\n🎉 终极数据库已生成！共融入了 {len(all_generals)} 个形态。")