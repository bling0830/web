from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import jieba
import numpy as np
import pickle
import json

class LightweightClassifier:
    def __init__(self):
        self.categories = {
            "正向价值观": ["爱国", "敬业", "诚信", "友善", "和谐", "公平", "正义"],
            "负向价值观": ["暴力", "歧视", "谣言", "极端", "违法", "不当言论"],
            "中性": ["客观描述", "日常交流"]
        }
        
        # 构建分类pipeline
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                tokenizer=self._tokenize,
                max_features=5000,
                ngram_range=(1, 2)
            )),
            ('classifier', LogisticRegression(
                multi_class='multinomial',
                max_iter=1000
            ))
        ])
        
        # 子类别分类器
        self.sub_classifiers = {}
        
    def _tokenize(self, text):
        # 使用jieba分词
        words = jieba.cut(text)
        # 过滤停用词
        return [w for w in words if len(w.strip()) > 1]
    
    def train(self, texts, labels):
        """训练主分类器"""
        X_train, X_val, y_train, y_val = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        self.pipeline.fit(X_train, y_train)
        
        # 评估
        val_score = self.pipeline.score(X_val, y_val)
        print(f"验证集准确率: {val_score:.4f}")
        
        # 训练子类别分类器
        self._train_sub_classifiers(texts, labels)
        
    def _train_sub_classifiers(self, texts, labels):
        """为每个主类别训练子类别分类器"""
        for main_category, sub_cats in self.categories.items():
            self.sub_classifiers[main_category] = {}
            for sub_cat in sub_cats:
                print(f"\n训练子分类器 - {main_category}/{sub_cat}")
                
                # 为每个子类别创建二元标签
                binary_labels = [1 if label == main_category else 0 for label in labels]
                
                clf = Pipeline([
                    ('tfidf', TfidfVectorizer(
                        tokenizer=self._tokenize,
                        max_features=5000,
                        ngram_range=(1, 2)
                    )),
                    ('classifier', LogisticRegression())
                ])
                clf.fit(texts, binary_labels)
                
                self.sub_classifiers[main_category][sub_cat] = clf
    
    def predict(self, text):
        """预测文本的类别"""
        # 主类别预测
        probs = self.pipeline.predict_proba([text])[0]
        pred_idx = np.argmax(probs)
        main_category = self.pipeline.classes_[pred_idx]
        confidence = probs[pred_idx]
        
        # 子类别预测
        sub_categories = self._predict_sub_categories(text, main_category)
        
        return {
            "category": main_category,
            "confidence": float(confidence),
            "sub_categories": sub_categories
        }
    
    def _predict_sub_categories(self, text, main_category):
        """预测子类别"""
        sub_categories = []
        
        if main_category in self.sub_classifiers:
            sub_clf_dict = self.sub_classifiers[main_category]
            for sub_cat, clf in sub_clf_dict.items():
                try:
                    if clf.predict([text])[0] == 1:
                        sub_categories.append(sub_cat)
                except Exception as e:
                    print(f"子类别预测错误 ({sub_cat}): {str(e)}")
                    continue
        
        # 如果没有预测出子类别，至少返回该主类别下的第一个子类别
        if not sub_categories and main_category in self.categories:
            sub_categories = [self.categories[main_category][0]]
        
        return sub_categories
    
    def _get_keywords(self, category):
        """获取类别相关的关键词"""
        keywords = {
            "爱国": ["祖国", "国家", "民族", "爱国"],
            "敬业": ["努力", "认真", "负责", "专注"],
            "诚信": ["诚实", "守信", "信用", "承诺"],
            "友善": ["友好", "善良", "关心", "帮助"],
            # ... 其他类别的关键词
        }
        return keywords.get(category, [category])
    
    def save(self, path):
        """保存模型"""
        with open(path, 'wb') as f:
            pickle.dump({
                'pipeline': self.pipeline,
                'sub_classifiers': self.sub_classifiers
            }, f)
    
    def load(self, path):
        """加载模型"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.pipeline = data['pipeline']
            self.sub_classifiers = data['sub_classifiers'] 