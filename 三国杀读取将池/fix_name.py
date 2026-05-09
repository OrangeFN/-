import os
import json
import hashlib

# 🚀 精准指向您的 HBuilderX 项目文件夹 (根据您的截图，路径是 sss)
base_dir = "D:/pycharm/sgs-2/sgsapp"
js_file = os.path.join(base_dir, "generals_data.js")

if not os.path.exists(js_file):
    print(f"❌ 找不到文件: {js_file}，请检查路径！")
    exit()

print("正在读取您的终极数据库...")
with open(js_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 剥离外壳，提取纯 JSON 数据
json_str = content.replace("const ALL_MERGED_GENERALS = ", "").rstrip(";")
data = json.loads(json_str)

count = 0
print("开始执行【物理图片改名】与【数据库同步修改】...")

for g in data:
    old_path = g.get('local_img_path', '')
    if old_path and 'images/' in old_path:
        # 生成绝对安全的纯英文数字文件名 (利用 MD5 算法)
        safe_name = "img_" + hashlib.md5(old_path.encode('utf-8')).hexdigest() + ".png"
        new_path = "images/" + safe_name

        # 拼接绝对路径
        old_file_full = os.path.join(base_dir, old_path)
        new_file_full = os.path.join(base_dir, new_path)

        # 1. 物理重命名图片文件
        if os.path.exists(old_file_full):
            try:
                os.rename(old_file_full, new_file_full)
                count += 1
            except Exception as e:
                print(f"改名失败: {old_path} -> {e}")

        # 2. 同步更新内存中的数据库路径
        g['local_img_path'] = new_path

# 将修复后的数据重新写回 JS 文件
print("正在重新封装数据库...")
with open(js_file, 'w', encoding='utf-8') as f:
    f.write("const ALL_MERGED_GENERALS = ")
    json.dump(data, f, ensure_ascii=False)
    f.write(";")

print(f"\n🎉 完美修复！成功将 {count} 张中文命名的图片转换成了安全的纯英文名，并且同步更新了代码！")
print("👉 现在您可以回到 HBuilderX 直接点击打包了！")