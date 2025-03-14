import os

def count_line(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return sum(1 for _ in file)

line = 0
# 统计当前文件夹下的所有文件的行数
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') or file.endswith('.html') or file.endswith('.js') or file.endswith('.css'):
            line += count_line(os.path.join(root, file))
print(line)
