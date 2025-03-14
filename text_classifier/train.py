import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .models import LightweightClassifier
from .data_processor import DataProcessor
import argparse

class Dataset:
    def __init__(self, texts, labels, tokenizer):
        self.encodings = tokenizer(texts, truncation=True, padding=True)
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: val[idx] for key, val in self.encodings.items()}
        item['labels'] = self.labels[idx]
        return item

    def __len__(self):
        return len(self.labels)

class DataLoader:
    def __init__(self, dataset, batch_size=32, shuffle=True):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indices = list(range(len(dataset)))
        
    def __iter__(self):
        if self.shuffle:
            import random
            random.shuffle(self.indices)
        
        for i in range(0, len(self.dataset), self.batch_size):
            batch_indices = self.indices[i:i + self.batch_size]
            batch = {}
            for idx in batch_indices:
                item = self.dataset[idx]
                for key, value in item.items():
                    if key not in batch:
                        batch[key] = []
                    batch[key].append(value)
            yield batch
    
    def __len__(self):
        return (len(self.dataset) + self.batch_size - 1) // self.batch_size

def train_model():
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, required=True)
    parser.add_argument('--model_path', type=str, default='models/classifier.pkl')
    args = parser.parse_args()
    
    # 初始化
    processor = DataProcessor()
    classifier = LightweightClassifier()
    
    # 加载数据
    texts, labels = processor.load_data(args.data_path)
    
    # 预处理
    texts = [processor.preprocess_text(text) for text in texts]
    
    # 数据增强
    texts, labels = processor.augment_data(texts, labels)
    
    # 训练模型
    print("开始训练模型...")
    classifier.train(texts, labels)
    
    # 保存模型
    classifier.save(args.model_path)
    print(f"模型已保存到: {args.model_path}")

if __name__ == '__main__':
    train_model() 