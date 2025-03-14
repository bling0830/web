from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from .models import LightweightClassifier
from .data_processor import DataProcessor
import sqlite3
from datetime import datetime
import json
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from openai import OpenAI
from typing import Optional

app = FastAPI()

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="text_classifier/static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="text_classifier/templates")

class TextRequest(BaseModel):
    text: str

class TrainingConfig(BaseModel):
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 0.001
    validation_split: float = 0.2

# 初始化
classifier = LightweightClassifier()
try:
    classifier.load('models/classifier.pkl')
except FileNotFoundError:
    print("警告：模型文件不存在，请先训练模型！")
    # 创建一个新的分类器实例
    classifier = LightweightClassifier()
processor = DataProcessor()

# 数据库连接
conn = sqlite3.connect('classifier.db')
cursor = conn.cursor()

# 创建表
cursor.execute('''
CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    main_category TEXT NOT NULL,
    sub_categories TEXT NOT NULL,
    confidence REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# 创建标注数据表
cursor.execute('''
CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    main_category TEXT NOT NULL,
    sub_categories TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'human' 或 'model'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()


@app.post("/classify")
async def classify_text(request: TextRequest):
    try:
        # 检查分类器是否正确初始化
        if not hasattr(classifier, 'predict') or not callable(classifier.predict):
            raise HTTPException(
                status_code=500, 
                detail="分类器未正确初始化，请确保模型已经训练"
            )

        # 检查输入文本
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail="输入文本不能为空"
            )

        # 预处理文本
        processed_text = processor.preprocess_text(request.text)
        
        # 预测
        prediction = classifier.predict(processed_text)
        
        # 构造返回结果
        result = {
            "category": str(prediction.get('category', '未知')),
            "sub_categories": prediction.get('sub_categories', []),
            "confidence": float(prediction.get('confidence', 0.0))
        }
        
        # 保存到数据库
        cursor.execute('''
        INSERT INTO classifications (text, main_category, sub_categories, confidence)
        VALUES (?, ?, ?, ?)
        ''', (
            request.text,
            result["category"],
            json.dumps(result["sub_categories"]),
            result["confidence"]
        ))
        conn.commit()  # 确保提交事务
        
        # 获取最新的历史记录
        cursor.execute('''
        SELECT * FROM classifications 
        ORDER BY timestamp DESC 
        LIMIT 10
        ''')
        
        columns = ['id', 'text', 'main_category', 'sub_categories', 
                  'confidence', 'timestamp']
        history = []
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['sub_categories'] = json.loads(item['sub_categories'])
            history.append(item)
        
        # 返回分类结果和最新历史记录
        return {
            "classification": result,
            "history": history
        }
        
    except Exception as e:
        print(f"分类错误: {str(e)}")  # 添加错误日志
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 10):
    try:
        # 添加调试日志
        print(f"获取历史记录，限制数量: {limit}")
        
        cursor.execute('''
        SELECT id, text, main_category, sub_categories, confidence, timestamp
        FROM classifications 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        columns = ['id', 'text', 'main_category', 'sub_categories', 
                  'confidence', 'timestamp']
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            # 确保 sub_categories 是 JSON 格式
            try:
                result['sub_categories'] = json.loads(result['sub_categories'])
            except:
                result['sub_categories'] = []
            results.append(result)
            
        # 添加调试日志
        print(f"找到 {len(results)} 条历史记录")
        return results
    except Exception as e:
        print(f"获取历史记录错误: {str(e)}")  # 添加错误日志
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    返回主页面
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/annotate")
async def annotate(request: Request):
    try:
        data = await request.json()
        
        # 插入标注数据
        cursor.execute('''
        INSERT INTO annotations 
        (text, main_category, sub_categories, source, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            data['text'],
            data['main_category'],
            json.dumps(data['sub_categories']),
            'human',
            datetime.now()
        ))
        conn.commit()
        
        # 立即返回新插入的数据
        return {
            "status": "success",
            "message": "标注成功",
            "annotation": {
                "text": data['text'],
                "main_category": data['main_category'],
                "sub_categories": data['sub_categories'],
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/annotations")
async def get_annotations():
    try:
        cursor.execute('''
        SELECT text, main_category, sub_categories, timestamp 
        FROM annotations 
        WHERE source = 'human'
        ORDER BY timestamp DESC
        LIMIT 100
        ''')
        
        columns = ['text', 'main_category', 'sub_categories', 'timestamp']
        annotations = []
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['sub_categories'] = json.loads(item['sub_categories'])
            annotations.append(item)
            
        return annotations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/training-data")
async def get_training_data(request: Request):
    """获取训练数据统计信息和详细数据"""
    try:
        # 获取数据总量和类别数
        cursor.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT main_category) as categories
        FROM annotations 
        WHERE source = 'human'
        ''')
        stats = dict(zip(['total', 'categories'], cursor.fetchone()))
        
        # 获取各类别数据分布
        cursor.execute('''
        SELECT main_category, COUNT(*) as count
        FROM annotations 
        WHERE source = 'human'
        GROUP BY main_category
        ''')
        category_distribution = dict(cursor.fetchall())
        
        # 获取详细的训练数据
        cursor.execute('''
        SELECT id, text, main_category, sub_categories, timestamp
        FROM annotations 
        WHERE source = 'human'
        ORDER BY timestamp DESC
        ''')
        
        columns = ['id', 'text', 'main_category', 'sub_categories', 'timestamp']
        detailed_data = []
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['sub_categories'] = json.loads(item['sub_categories'])
            detailed_data.append(item)
        
        return {
            "stats": stats,
            "distribution": category_distribution,
            "data": detailed_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrain")
async def retrain_model(config: TrainingConfig):
    try:
        # 获取所有人工标注数据
        cursor.execute('''
        SELECT text, main_category, sub_categories 
        FROM annotations 
        WHERE source = 'human'
        ''')
        
        training_data = []
        for row in cursor.fetchall():
            text, category, sub_categories = row
            training_data.append({
                'text': text,
                'category': category,
                'sub_categories': json.loads(sub_categories)
            })
        
        if not training_data:
            raise HTTPException(status_code=400, detail="没有足够的训练数据")
        
        try:
            # 打印调试信息
            print(f"训练数据数量: {len(training_data)}")
            print(f"训练配置: {config}")
            
            # 使用配置参数重新训练模型
            classifier.train(
                [item['text'] for item in training_data],
                [item['category'] for item in training_data]
                # 注意：移除了额外的参数，因为 LightweightClassifier 的 train 方法可能不接受这些参数
            )
            
            # 保存模型
            classifier.save('models/classifier.pkl')
            
            return {
                "status": "success", 
                "message": "模型重新训练完成",
                "config": config.dict()
            }
        except Exception as e:
            print(f"训练过程错误: {str(e)}")  # 打印具体错误信息
            raise HTTPException(status_code=500, detail=f"训练过程错误: {str(e)}")
            
    except Exception as e:
        print(f"重训练接口错误: {str(e)}")  # 打印具体错误信息
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/training", response_class=HTMLResponse)
async def training_page(request: Request):
    """返回训练页面"""
    return templates.TemplateResponse(
        "training.html",
        {"request": request}
    )

@app.post("/import-annotations")
async def import_annotations(request: Request):
    try:
        data = await request.json()
        for item in data:
            cursor.execute('''
            INSERT INTO annotations (text, main_category, sub_categories, source)
            VALUES (?, ?, ?, ?)
            ''', (
                item['text'],
                item['main_category'],
                json.dumps(item['sub_categories']),
                'human'
            ))
        conn.commit()
        return {"status": "success", "message": f"成功导入{len(data)}条数据"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export-annotations")
async def export_annotations():
    try:
        cursor.execute('SELECT * FROM annotations WHERE source = "human"')
        data = cursor.fetchall()
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-annotation")
async def review_annotation(request: Request):
    data = await request.json()
    try:
        cursor.execute('''
        UPDATE annotations 
        SET review_status = ?, reviewer_comments = ?
        WHERE id = ?
        ''', (
            data['status'],  # 'approved' 或 'rejected'
            data['comments'],
            data['annotation_id']
        ))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/annotation-stats")
async def get_annotation_stats():
    try:
        # 按时间统计
        cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM annotations
        WHERE source = 'human'
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        ''')
        daily_stats = dict(cursor.fetchall())
        
        # 按标注者统计
        cursor.execute('''
        SELECT annotator, COUNT(*) as count
        FROM annotations
        WHERE source = 'human'
        GROUP BY annotator
        ''')
        annotator_stats = dict(cursor.fetchall())
        
        return {
            "daily_stats": daily_stats,
            "annotator_stats": annotator_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate-model")
async def evaluate_model():
    try:
        # 获取测试数据
        cursor.execute('''
        SELECT text, main_category, sub_categories
        FROM annotations
        WHERE source = 'human' AND is_test_set = 1
        ''')
        test_data = cursor.fetchall()
        
        results = []
        for text, true_category, true_sub_categories in test_data:
            prediction = classifier.predict(text)
            results.append({
                "text": text,
                "true_category": true_category,
                "predicted_category": prediction["category"],
                "confidence": prediction["confidence"]
            })
            
        return {
            "evaluation_results": results,
            "accuracy": sum(1 for r in results if r["true_category"] == r["predicted_category"]) / len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-suggestion")
async def get_ai_suggestion(request: TextRequest):
    try:
        text = request.text
        
        # 构建 prompt
        prompt = f"""请分析以下文本的价值观倾向，并给出详细解释。
文本："{text}"

请从以下类别中选择：
主类别：
- 正向价值观（包含：爱国、敬业、诚信、友善、和谐、公平、正义）
- 负向价值观（包含：暴力、歧视、谣言、极端、违法、不当言论）
- 中性（包含：客观描述、日常交流）

请按照以下格式输出：
主类别：[类别名]
子类别：[相关的具体子类别，可多选]
分析理由：[详细解释为什么属于这个类别]"""

        client = OpenAI(
            base_url='https://api.openai-proxy.org/v1',
            api_key='sk-nJcHY4m9MtnA5BfE6y9mnsKe1Kcz9JiAB6F4YYvt6WHhqres',
        )

        # 调用 OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的文本分类助手，擅长分析文本中的价值观倾向。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # 解析 AI 响应
        ai_response = response.choices[0].message.content
        print(ai_response)
        # 解析响应内容
        category = ""
        sub_categories = []
        explanation = ""
        
        # 更精确的响应解析
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('主类别：'):
                category = line.replace('主类别：', '').strip()
            elif line.startswith('子类别：'):
                sub_cats = line.replace('子类别：', '').strip()
                # 处理可能的不同分隔符
                if '、' in sub_cats:
                    sub_categories = [cat.strip() for cat in sub_cats.split('、')]
                elif ',' in sub_cats:
                    sub_categories = [cat.strip() for cat in sub_cats.split(',')]
                elif '，' in sub_cats:
                    sub_categories = [cat.strip() for cat in sub_cats.split('，')]
                else:
                    sub_categories = [sub_cats]
                # 过滤空字符串
                sub_categories = [cat for cat in sub_categories if cat]
            elif line.startswith('分析理由：'):
                explanation = line.replace('分析理由：', '').strip()
        
        # 获取模型的分类结果
        model_prediction = classifier.predict(text)
        
        # 打印调试信息
        print(f"AI Response: {ai_response}")
        print(f"Parsed Category: {category}")
        print(f"Parsed Sub-categories: {sub_categories}")
        print(f"Parsed Explanation: {explanation}")
        
        return {
            "category": category,
            "sub_categories": sub_categories,
            "explanation": explanation,
            "model_prediction": {
                "category": model_prediction["category"],
                "sub_categories": model_prediction["sub_categories"],
                "confidence": model_prediction["confidence"]
            }
        }
        
    except Exception as e:
        print(f"AI建议生成错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 