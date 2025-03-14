async function classifyText() {
    const text = document.getElementById('input-text').value;
    if (!text) {
        showNotification('请输入文本', 'warning');
        return;
    }

    const resultBox = document.getElementById('result');
    resultBox.classList.remove('hidden');
    showLoading(true);

    try {
        const response = await fetch('/classify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        
        // 直接调用 displayResult 显示分类结果
        displayResult(data.classification);
        
        // 更新历史记录
        if (data.history) {
            updateHistory(data.history);
        }
        
        showLoading(false);
        showNotification('分类完成', 'success');
    } catch (error) {
        console.error('分类错误:', error);
        showLoading(false);
        showNotification('分类过程中发生错误', 'error');
    }
}

function displayResult(result) {
    const resultContent = document.querySelector('.result-content');
    if (!resultContent) {
        console.error('找不到结果显示容器');
        return;
    }

    // 获取原始输入文本
    const inputText = document.getElementById('input-text').value;

    // 确保所有数据都存在并有默认值
    const category = result.category || '未知';
    const subCategories = result.sub_categories || [];
    const confidence = result.confidence || 0;

    resultContent.innerHTML = `
        <div class="result-item">
            <div class="result-label">输入文本：</div>
            <div class="result-value">${inputText}</div>
        </div>
        <div class="result-item">
            <div class="result-label">主类别：</div>
            <div class="result-value">${category}</div>
        </div>
        <div class="result-item">
            <div class="result-label">子类别：</div>
            <div class="result-value">${formatSubCategories(subCategories)}</div>
        </div>
        <div class="result-item">
            <div class="result-label">置信度：</div>
            <div class="result-value">${(confidence * 100).toFixed(2)}%</div>
        </div>
    `;

    // 显示结果容器
    document.getElementById('result').classList.remove('hidden');
}

function formatSubCategories(subCategories) {
    return Array.isArray(subCategories) 
        ? subCategories.join(', ')
        : JSON.stringify(subCategories);
}

async function loadHistory() {
    try {
        const response = await fetch('/history?limit=10');
        const history = await response.json();
        updateHistory(history);  // 使用统一的更新函数
    } catch (error) {
        console.error('Error:', error);
        showNotification('加载历史记录失败', 'error');
    }
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`${tabName}-tab`).classList.add('active');
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
    
    // 如果切换到标注标签页，重新加载标注数据
    if (tabName === 'annotate') {
        loadAnnotations();
    }
}

// 添加类别配置
const categoryConfig = {
    "正向价值观": ["爱国", "敬业", "诚信", "友善", "和谐", "公平", "正义"],
    "负向价值观": ["暴力", "歧视", "谣言", "极端", "违法", "不当言论"],
    "中性": ["客观描述", "日常交流"]
};

// 当主类别改变时更新子类别选项
document.getElementById('main-category').addEventListener('change', function() {
    const mainCategory = this.value;
    const subContainer = document.getElementById('sub-categories-container');
    subContainer.innerHTML = '';
    
    if (mainCategory && categoryConfig[mainCategory]) {
        categoryConfig[mainCategory].forEach(subCat => {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'checkbox-item';
            checkboxDiv.innerHTML = `
                <input type="checkbox" id="sub-${subCat}" value="${subCat}">
                <label for="sub-${subCat}">${subCat}</label>
            `;
            subContainer.appendChild(checkboxDiv);
        });
    }
});

// 修改清空表单函数
function clearAnnotationForm() {
    // 清空文本框
    document.getElementById('annotate-text').value = '';
    
    // 清空主类别选择
    document.getElementById('main-category').value = '';
    
    // 清空子类别选择框
    const subContainer = document.getElementById('sub-categories-container');
    subContainer.innerHTML = '';
    
    // 移除所有选中状态
    document.querySelectorAll('#sub-categories-container input[type="checkbox"]')
        .forEach(checkbox => checkbox.checked = false);
}

// 修改提交标注函数
async function submitAnnotation() {
    const text = document.getElementById('annotate-text').value;
    const mainCategory = document.getElementById('main-category').value;
    
    const subCategories = Array.from(
        document.querySelectorAll('#sub-categories-container input[type="checkbox"]:checked')
    ).map(cb => cb.value);
    
    if (!text || !mainCategory || !subCategories.length) {
        showNotification('请填写完整的标注信息', 'warning');
        return;
    }

    try {
        const response = await fetch('/annotate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                main_category: mainCategory,
                sub_categories: subCategories
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // 先重新加载标注数据
            await loadAnnotations();
            
            // 再清空表单
            clearAnnotationForm();
            
            // 显示成功提示
            showNotification('标注成功', 'success');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('标注失败，请重试', 'error');
    }
}

function updateAnnotationsTable(annotations) {
    const tableBody = document.querySelector('#annotations-table tbody');
    if (!tableBody) {
        console.error('找不到标注数据表格');
        return;
    }
    
    // 清空现有数据
    tableBody.innerHTML = '';
    
    // 添加新数据
    annotations.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.text}</td>
            <td>${item.main_category}</td>
            <td>${Array.isArray(item.sub_categories) ? item.sub_categories.join(', ') : item.sub_categories}</td>
            <td>${new Date(item.timestamp).toLocaleString()}</td>
        `;
        tableBody.appendChild(tr);
    });
}

async function loadAnnotations() {
    try {
        const response = await fetch('/annotations');
        const annotations = await response.json();
        
        const tableBody = document.querySelector('#annotations-table tbody');
        if (!tableBody) {
            console.error('找不到标注数据表格');
            return;
        }
        
        // 清空现有数据
        tableBody.innerHTML = '';
        
        // 添加新数据
        annotations.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.text}</td>
                <td>${item.main_category}</td>
                <td>${Array.isArray(item.sub_categories) ? item.sub_categories.join(', ') : item.sub_categories}</td>
                <td>${new Date(item.timestamp).toLocaleString()}</td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error:', error);
        showNotification('加载标注数据失败', 'error');
    }
}

async function retrainModel() {
    const statusBox = document.getElementById('training-status');
    const messageEl = document.getElementById('training-message');
    const dataCountEl = document.getElementById('data-count');
    const timeEl = document.getElementById('training-time');
    let startTime = Date.now();
    
    try {
        // 显示训练状态
        statusBox.classList.remove('hidden');
        messageEl.textContent = '正在准备训练数据...';
        
        // 获取训练数据统计
        const statsResponse = await fetch('/training-data');
        const statsData = await statsResponse.json();
        dataCountEl.textContent = statsData.stats.total;
        
        // 开始训练
        messageEl.textContent = '模型训练中...';
        showNotification('模型重训练开始...', 'info');
        
        const response = await fetch('/retrain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                epochs: 10,
                batch_size: 32,
                learning_rate: 0.001,
                validation_split: 0.2
            })
        });
        
        if (!response.ok) {
            throw new Error('服务器响应错误');
        }
        
        const result = await response.json();
        
        // 更新训练状态
        const trainingTime = ((Date.now() - startTime) / 1000).toFixed(1);
        timeEl.textContent = trainingTime;
        messageEl.textContent = '训练完成！';
        
        showNotification(result.message || '模型重训练完成', 'success');
        
        // 3秒后隐藏状态框
        setTimeout(() => {
            statusBox.classList.add('hidden');
        }, 3000);
        
    } catch (error) {
        console.error('重训练错误:', error);
        messageEl.textContent = '训练失败: ' + error.message;
        showNotification('模型重训练失败，请重试', 'error');
        
        // 3秒后隐藏状态框
        setTimeout(() => {
            statusBox.classList.add('hidden');
        }, 3000);
    }
}

function showLoading(show) {
    const loader = document.querySelector('.loader');
    if (show) {
        loader.classList.remove('hidden');
    } else {
        loader.classList.add('hidden');
    }
}

function updateHistory(history) {
    const historyContainer = document.getElementById('history-list');
    if (!historyContainer) {
        console.error('找不到历史记录容器元素');
        return;
    }
    
    // 添加调试日志
    console.log('更新历史记录:', history);
    
    historyContainer.innerHTML = ''; // 清空现有历史记录
    
    if (!history || history.length === 0) {
        historyContainer.innerHTML = '<div class="history-item">暂无历史记录</div>';
        return;
    }
    
    history.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <p><strong>文本:</strong> ${item.text}</p>
            <p><strong>主类别:</strong> ${item.main_category}</p>
            <p><strong>子类别:</strong> ${Array.isArray(item.sub_categories) ? item.sub_categories.join(', ') : item.sub_categories}</p>
            <p><strong>置信度:</strong> ${(item.confidence * 100).toFixed(2)}%</p>
            <p><strong>时间:</strong> ${new Date(item.timestamp).toLocaleString()}</p>
        `;
        historyContainer.appendChild(historyItem);
    });
}

// 页面加载时加载历史记录
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/history?limit=10');
        const history = await response.json();
        console.log('加载历史记录:', history); // 添加调试日志
        updateHistory(history);
    } catch (error) {
        console.error('加载历史记录失败:', error);
        showNotification('加载历史记录失败', 'error');
    }
});

// 确保 retrainModel 函数被正确调用
document.addEventListener('DOMContentLoaded', function() {
    // 为重训练按钮添加事件监听器
    const retrainBtn = document.querySelector('.secondary-btn');
    if (retrainBtn) {
        retrainBtn.addEventListener('click', async function(e) {
            e.preventDefault(); // 防止表单提交
            console.log('开始重训练...'); // 添加调试日志
            await retrainModel();
        });
    }
});

function showNotification(message, type = 'info') {
    console.log('显示通知:', message, type); // 添加调试日志
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 添加到页面
    const container = document.querySelector('.main-content') || document.body;
    container.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 添加新的请求函数
async function requestAISuggestion() {
    const text = document.getElementById('annotate-text').value;
    
    if (!text.trim()) {
        showNotification('请先输入文本', 'warning');
        return;
    }
    
    if (text.trim().length < 5) {
        showNotification('文本长度需要大于5个字符', 'warning');
        return;
    }

    const suggestionContent = document.querySelector('.suggestion-content');
    if (!suggestionContent) return;

    try {
        // 显示加载状态
        suggestionContent.innerHTML = `
            <div class="suggestion-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span style="margin-left: 10px">正在获取AI建议...</span>
            </div>
        `;

        const response = await fetch('/ai-suggestion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text })
        });
        
        if (!response.ok) {
            throw new Error('获取AI建议失败');
        }
        
        const suggestion = await response.json();
        displayAISuggestion(suggestion);
        showNotification('AI建议获取成功', 'success');
    } catch (error) {
        console.error('获取AI建议失败:', error);
        suggestionContent.innerHTML = `
            <div class="suggestion-error">
                <i class="fas fa-exclamation-circle"></i>
                获取AI建议失败: ${error.message}
            </div>
        `;
        showNotification('获取AI建议失败', 'error');
    }
}

function displayAISuggestion(suggestion) {
    const suggestionContent = document.querySelector('.suggestion-content');
    if (!suggestionContent) return;
    
    suggestionContent.innerHTML = `
        <div class="suggestion-item">
            <div class="suggestion-label">AI建议主类别：</div>
            <div class="suggestion-value">${suggestion.category || '未知'}</div>
        </div>
        <div class="suggestion-item">
            <div class="suggestion-label">AI建议子类别：</div>
            <div class="suggestion-value">${suggestion.sub_categories?.join('、') || '无'}</div>
        </div>
        <div class="suggestion-item">
            <div class="suggestion-label">分析理由：</div>
            <div class="suggestion-value">${suggestion.explanation || '无'}</div>
        </div>
        <div class="suggestion-item model-prediction">
            <div class="suggestion-label">模型预测：</div>
            <div class="suggestion-value">
                <p>主类别：${suggestion.model_prediction?.category || '未知'}</p>
                <p>子类别：${suggestion.model_prediction?.sub_categories?.join('、') || '无'}</p>
                <p>置信度：${(suggestion.model_prediction?.confidence * 100 || 0).toFixed(2)}%</p>
            </div>
        </div>
    `;
} 