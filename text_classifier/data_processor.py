import pandas as pd
import json
from sklearn.model_selection import train_test_split

class DataProcessor:
    def __init__(self):
        self.stopwords = self._load_stopwords()
    
    def _load_stopwords(self):
        # 加载停用词表
        try:
            with open('data/stopwords.txt', 'r', encoding='utf-8') as f:
                return set([line.strip() for line in f])
        except:
            return set()
    
    def load_data(self, file_path):
        """加载训练数据"""
        df = pd.read_csv(file_path)
        texts = df['text'].tolist()
        labels = df['category'].tolist()
        return texts, labels
    
    def preprocess_text(self, text):
        """文本预处理"""
        # 去除特殊字符
        text = ''.join([char for char in text if '\u4e00' <= char <= '\u9fff' or char.isspace()])
        # 去除多余空格
        text = ' '.join(text.split())
        return text
    
    def augment_data(self, texts, labels):
        """数据增强"""
        augmented_texts = []
        augmented_labels = []
        
        for text, label in zip(texts, labels):
            # 原始数据
            augmented_texts.append(text)
            augmented_labels.append(label)
            
            # 随机删除部分词语
            words = text.split()
            if len(words) > 5:
                reduced_text = ' '.join(words[::2])  # 每隔一个词保留
                augmented_texts.append(reduced_text)
                augmented_labels.append(label)
        
        return augmented_texts, augmented_labels 