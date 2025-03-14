import pandas as pd

# 创建示例数据
sample_data = {
    'text': [
        '我们要热爱祖国，为人民服务',
        '认真工作，勤勤恳恳',
        '散布谣言害人不浅',
        '和谐友善的社会氛围',
        '客观公正地看待问题'
    ],
    'category': [
        '正向价值观',
        '正向价值观',
        '负向价值观',
        '正向价值观',
        '中性'
    ]
}

# 创建DataFrame并保存
df = pd.DataFrame(sample_data)
df.to_csv('data/train.csv', index=False) 