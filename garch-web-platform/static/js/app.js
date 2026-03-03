// GARCH Web Platform - Main Application JavaScript

// 全局状态变量
let uploadedFile = null;
let selectedSheet = null;
let columnMapping = {
    spot: null,
    future: null,
    date: null
};

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadArea();
});

/**
 * 初始化文件上传区域
 */
function initializeUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    if (!uploadArea || !fileInput) {
        console.error('上传区域未找到');
        return;
    }

    // 点击上传区域触发文件选择
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // 文件选择事件
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // 拖拽事件处理
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    console.log('文件上传区域初始化完成');
}

/**
 * 处理文件上传
 */
async function handleFileUpload(file) {
    // 验证文件类型
    const validExtensions = ['.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    const isValidFile = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValidFile) {
        showError('不支持的文件格式，请上传Excel文件 (.xlsx, .xls)');
        return;
    }

    // 验证文件大小（50MB）
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('文件过大，请上传小于50MB的文件');
        return;
    }

    // 显示上传中状态
    showUploadProgress(file.name);

    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);

    try {
        // 发送上传请求
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '上传失败');
        }

        // 保存文件信息
        uploadedFile = {
            name: result.filename,
            path: result.filepath,
            originalName: file.name
        };

        // 显示成功消息
        showSuccess(result.message || '文件上传成功');

        // 显示工作表选择
        displaySheets(result.sheets, result.recommended_sheet);

        // 自动加载推荐的工作表
        if (result.recommended_sheet) {
            await loadSheetPreview(result.recommended_sheet);
        }

    } catch (error) {
        console.error('上传错误:', error);
        showError(error.message || '文件上传失败，请重试');
        resetUploadArea();
    }
}

/**
 * 显示上传进度
 */
function showUploadProgress(fileName) {
    const uploadArea = document.getElementById('upload-area');
    if (!uploadArea) return;

    uploadArea.innerHTML = `
        <div class="upload-progress">
            <div class="spinner"></div>
            <p>正在上传: ${fileName}</p>
            <p class="text-muted">请稍候...</p>
        </div>
    `;
}

/**
 * 重置上传区域
 */
function resetUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    if (!uploadArea || !fileInput) return;

    uploadArea.innerHTML = `
        <div class="upload-icon">📁</div>
        <h3>拖拽Excel文件到此处</h3>
        <p>或点击选择文件</p>
        <p class="text-muted">支持 .xlsx, .xls 格式，最大50MB</p>
    `;
    fileInput.value = '';
}

/**
 * 显示错误消息
 */
function showError(message) {
    // 检查是否有错误容器
    let errorContainer = document.getElementById('error-container');

    // 如果没有，创建一个
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.id = 'error-container';
        errorContainer.className = 'error-container';
        document.querySelector('.container').prepend(errorContainer);
    }

    errorContainer.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>错误：</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // 5秒后自动隐藏
    setTimeout(() => {
        errorContainer.innerHTML = '';
    }, 5000);

    console.error('错误:', message);
}

/**
 * 显示成功消息
 */
function showSuccess(message) {
    // 检查是否有消息容器
    let messageContainer = document.getElementById('message-container');

    // 如果没有，创建一个
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'message-container';
        messageContainer.className = 'message-container';
        document.querySelector('.container').prepend(messageContainer);
    }

    messageContainer.innerHTML = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>成功：</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // 5秒后自动隐藏
    setTimeout(() => {
        messageContainer.innerHTML = '';
    }, 5000);

    console.log('成功:', message);
}

/**
 * 显示信息消息
 */
function showInfo(message) {
    // 检查是否有消息容器
    let messageContainer = document.getElementById('message-container');

    // 如果没有，创建一个
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'message-container';
        messageContainer.className = 'message-container';
        document.querySelector('.container').prepend(messageContainer);
    }

    messageContainer.innerHTML = `
        <div class="alert alert-info alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // 3秒后自动隐藏
    setTimeout(() => {
        messageContainer.innerHTML = '';
    }, 3000);
}

/**
 * 显示工作表选择列表
 * @param {Array} sheets - 工作表信息数组
 * @param {string} recommended - 推荐的工作表名称
 */
function displaySheets(sheets, recommended) {
    const sheetSelect = document.getElementById('sheetSelect');
    const sheetSelection = document.getElementById('sheetSelection');

    if (!sheetSelect || !sheetSelection) {
        console.error('工作表选择元素未找到');
        return;
    }

    // 清空现有选项
    sheetSelect.innerHTML = '<option value="">-- 请选择工作表 --</option>';

    // 添加工作表选项
    sheets.forEach(sheet => {
        if (sheet.error) {
            console.warn(`工作表 ${sheet.name} 读取失败: ${sheet.error}`);
            return;
        }

        const option = document.createElement('option');
        option.value = sheet.name;

        // 显示工作表信息
        let infoText = sheet.name;
        if (sheet.row_count !== undefined) {
            infoText += ` (${sheet.row_count} 行`;
            if (sheet.column_count !== undefined) {
                infoText += ` × ${sheet.column_count} 列`;
            }
            infoText += ')';
        }

        // 标记推荐的工作表
        if (sheet.name === recommended) {
            infoText += ' ⭐ 推荐';
            option.selected = true;
        }

        option.textContent = infoText;
        sheetSelect.appendChild(option);
    });

    // 显示工作表选择区域
    sheetSelection.style.display = 'block';

    // 添加工作表选择变更事件监听器
    sheetSelect.onchange = async function() {
        const selectedValue = this.value;
        if (selectedValue) {
            await loadSheetPreview(selectedValue);
        }
    };

    console.log('工作表列表已显示，推荐:', recommended);
}


/**
 * 加载工作表预览
 * @param {string} sheetName - 工作表名称
 */
async function loadSheetPreview(sheetName) {
    if (!uploadedFile) {
        showError('文件信息丢失，请重新上传文件');
        return;
    }

    selectedSheet = sheetName;
    console.log('加载工作表预览:', sheetName);

    try {
        const response = await fetch('/api/preview-sheet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filepath: uploadedFile.path,
                sheet_name: sheetName
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '加载预览失败');
        }

        // 显示数据预览
        displayDataPreview(result.preview.preview_data);

        // 显示日期范围
        if (result.preview.date_range) {
            displayDateRange(result.preview.date_range);
        }

        // 显示列映射
        displayColumnMapping(result.preview.columns, result.suggested_columns);

        // 显示步骤2和步骤3
        showStep2();

        showSuccess(`工作表 "${sheetName}" 加载成功`);

    } catch (error) {
        console.error('加载预览错误:', error);
        showError(error.message || '加载工作表预览失败');
    }
}


/**
 * 显示数据预览表格
 * @param {Array} previewData - 预览数据数组
 */
function displayDataPreview(previewData) {
    const dataPreview = document.getElementById('dataPreview');

    if (!dataPreview) {
        console.error('数据预览容器未找到');
        return;
    }

    if (!previewData || previewData.length === 0) {
        dataPreview.innerHTML = '<p style="color: #e74c3c;">无数据</p>';
        return;
    }

    // 创建表格
    let tableHTML = '<table class="preview-table">';

    // 表头
    tableHTML += '<thead><tr>';
    const columns = Object.keys(previewData[0]);
    columns.forEach(col => {
        tableHTML += `<th>${col}</th>`;
    });
    tableHTML += '</tr></thead>';

    // 表体
    tableHTML += '<tbody>';
    previewData.forEach((row, index) => {
        tableHTML += `<tr class="${index % 2 === 0 ? 'even-row' : 'odd-row'}">`;
        columns.forEach(col => {
            const value = row[col];
            const displayValue = value !== null && value !== undefined ? value : '';
            tableHTML += `<td>${displayValue}</td>`;
        });
        tableHTML += '</tr>';
    });
    tableHTML += '</tbody></table>';

    // 添加数据信息
    tableHTML += `<div class="preview-info">显示前 ${previewData.length} 行数据</div>`;

    dataPreview.innerHTML = tableHTML;
    console.log('数据预览已显示，共', previewData.length, '行');
}


/**
 * 显示日期范围
 * @param {Object} dateRange - 日期范围对象 {start, end, count}
 */
function displayDateRange(dateRange) {
    // 这个功能将在后续步骤中使用
    // 目前我们只是保存日期范围信息
    console.log('日期范围:', dateRange);

    // 如果有日期输入框，可以在这里设置默认值
    // 目前模板中没有日期范围输入框，所以先保存到全局状态
    if (window.GARCHApp) {
        window.GARCHApp.dateRange = dateRange;
    }
}


/**
 * 显示列映射选择器
 * @param {Array} columns - 列名数组
 * @param {Object} suggested - 推荐的列映射 {spot, future, date}
 */
function displayColumnMapping(columns, suggested) {
    const spotSelect = document.getElementById('spotColumn');
    const futureSelect = document.getElementById('futuresColumn');
    const dateSelect = document.getElementById('dateColumn');
    const columnMapping = document.getElementById('columnMapping');
    const confirmBtn = document.getElementById('confirmColumnsBtn');

    if (!spotSelect || !futureSelect || !dateSelect || !columnMapping) {
        console.error('列映射元素未找到');
        return;
    }

    // 清空现有选项
    spotSelect.innerHTML = '<option value="">-- 请选择 --</option>';
    futureSelect.innerHTML = '<option value="">-- 请选择 --</option>';
    dateSelect.innerHTML = '<option value="">-- 不使用日期 --</option>';

    // 添加列选项
    columns.forEach(col => {
        // 现货价格列
        const spotOption = document.createElement('option');
        spotOption.value = col;
        spotOption.textContent = col;
        if (col === suggested.spot) {
            spotOption.selected = true;
        }
        spotSelect.appendChild(spotOption);

        // 期货价格列
        const futureOption = document.createElement('option');
        futureOption.value = col;
        futureOption.textContent = col;
        if (col === suggested.future) {
            futureOption.selected = true;
        }
        futureSelect.appendChild(futureOption);

        // 日期列
        const dateOption = document.createElement('option');
        dateOption.value = col;
        dateOption.textContent = col;
        if (col === suggested.date) {
            dateOption.selected = true;
        }
        dateSelect.appendChild(dateOption);
    });

    // 显示列映射区域
    columnMapping.style.display = 'block';

    // 更新全局列映射状态
    columnMapping.spot = suggested.spot;
    columnMapping.future = suggested.future;
    columnMapping.date = suggested.date;

    // 添加列变更监听器
    const updateColumnMapping = () => {
        columnMapping.spot = spotSelect.value;
        columnMapping.future = futureSelect.value;
        columnMapping.date = dateSelect.value;

        // 启用/禁用确认按钮
        if (columnMapping.spot && columnMapping.future) {
            confirmBtn.disabled = false;
        } else {
            confirmBtn.disabled = true;
        }
    };

    spotSelect.onchange = updateColumnMapping;
    futureSelect.onchange = updateColumnMapping;
    dateSelect.onchange = updateColumnMapping;

    // 初始化按钮状态
    updateColumnMapping();

    console.log('列映射已显示:', suggested);
}


/**
 * 显示步骤2（工作表选择和数据预览）
 */
function showStep2() {
    const sheetSelection = document.getElementById('sheetSelection');
    const columnMapping = document.getElementById('columnMapping');

    if (sheetSelection) {
        sheetSelection.style.display = 'block';
    }

    if (columnMapping) {
        // 列映射区域已在 displayColumnMapping 中显示
        columnMapping.style.display = 'block';
    }

    // 滚动到工作表选择区域
    if (sheetSelection) {
        sheetSelection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}


// 列映射确认按钮事件
document.addEventListener('DOMContentLoaded', function() {
    const confirmBtn = document.getElementById('confirmColumnsBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            // 显示模型选择区域
            const modelSelection = document.getElementById('modelSelection');
            if (modelSelection) {
                modelSelection.style.display = 'block';
                modelSelection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            showSuccess('列配置已确认，请选择模型并运行');
        });
    }

    // 训练集比例滑块
    const trainSizeInput = document.getElementById('trainSize');
    const trainSizeValue = document.getElementById('trainSizeValue');
    if (trainSizeInput && trainSizeValue) {
        trainSizeInput.addEventListener('input', function() {
            trainSizeValue.textContent = this.value + '%';
        });
    }

    // 运行模型按钮
    const runModelBtn = document.getElementById('runModelBtn');
    if (runModelBtn) {
        runModelBtn.addEventListener('click', generateReport);
    }
});


/**
 * 生成分析报告
 */
async function generateReport() {
    if (!uploadedFile || !selectedSheet) {
        showError('请先上传文件并选择工作表');
        return;
    }

    // 获取选中的模型
    const modelRadio = document.querySelector('input[name="model"]:checked');
    if (!modelRadio) {
        showError('请选择一个模型');
        return;
    }

    const modelType = modelRadio.value;

    // 获取列映射
    const spotColumn = document.getElementById('spotColumn')?.value;
    const futuresColumn = document.getElementById('futuresColumn')?.value;
    const dateColumn = document.getElementById('dateColumn')?.value;

    if (!spotColumn || !futuresColumn) {
        showError('请配置现货和期货价格列');
        return;
    }

    const columnMapping = {
        spot: spotColumn,
        future: futuresColumn,
        date: dateColumn || null
    };

    // 显示进度
    showProgress('正在运行模型分析...');

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filepath: uploadedFile.path,
                sheet_name: selectedSheet,
                column_mapping: columnMapping,
                date_range: null,
                model_type: modelType
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '生成报告失败');
        }

        // 隐藏进度
        hideProgress();

        // 显示结果
        displayResult(result);

        showSuccess(`${result.message || '分析完成'}`);

    } catch (error) {
        hideProgress();
        console.error('生成报告错误:', error);
        showError(error.message || '生成报告失败，请重试');
    }
}


/**
 * 显示进度条
 */
function showProgress(message) {
    const progressArea = document.getElementById('progressArea');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    if (progressArea) {
        progressArea.style.display = 'block';
    }
    if (progressText) {
        progressText.textContent = message;
    }
    if (progressBar) {
        progressBar.style.width = '0%';
        // 模拟进度动画
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
        }, 500);

        // 保存interval ID以便清除
        progressArea.dataset.intervalId = interval;
    }
}


/**
 * 隐藏进度条
 */
function hideProgress() {
    const progressArea = document.getElementById('progressArea');
    const progressBar = document.getElementById('progressBar');

    if (progressArea) {
        // 清除进度动画
        if (progressArea.dataset.intervalId) {
            clearInterval(parseInt(progressArea.dataset.intervalId));
        }
        progressArea.style.display = 'none';
    }
    if (progressBar) {
        progressBar.style.width = '100%';
    }
}


/**
 * 显示分析结果
 */
function displayResult(result) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    if (!resultsSection || !resultsContent) {
        console.error('结果区域未找到');
        return;
    }

    const summary = result.summary || {};

    // 构建结果HTML
    let html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; opacity: 0.9;">套保比例均值</div>
                <div style="font-size: 24px; font-weight: bold;">${(summary.hedge_ratio_mean || 0).toFixed(4)}</div>
            </div>
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; opacity: 0.9;">方差降低</div>
                <div style="font-size: 24px; font-weight: bold;">${((summary.variance_reduction || 0) * 100).toFixed(2)}%</div>
            </div>
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; opacity: 0.9;">Ederington有效性</div>
                <div style="font-size: 24px; font-weight: bold;">${(summary.ederington || 0).toFixed(4)}</div>
            </div>
        </div>

        <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
            <a href="${result.view_url}" target="_blank" class="btn" style="background-color: #3498db; color: white; text-decoration: none; padding: 12px 24px; border-radius: 4px; display: inline-block;">
                📊 查看HTML报告
            </a>
            <a href="${result.download_url}" class="btn" style="background-color: #2ecc71; color: white; text-decoration: none; padding: 12px 24px; border-radius: 4px; display: inline-block;">
                📥 下载ZIP包
            </a>
            <button onclick="resetAnalysis()" class="btn" style="background-color: #e74c3c; color: white; padding: 12px 24px; border-radius: 4px; border: none; cursor: pointer;">
                🔄 重新分析
            </button>
        </div>
    `;

    // 添加额外的模型特定信息
    if (summary.model_name) {
        html += `
            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #3498db;">
                <h3 style="margin-top: 0; color: #2c3e50;">模型信息</h3>
                <p><strong>模型类型：</strong>${summary.model_name}</p>
                <p><strong>模型参数：</strong>${summary.model_params || 'N/A'}</p>
                ${summary.error_correction_coeff ? `<p><strong>误差修正系数：</strong>${summary.error_correction_coeff.toFixed(6)}</p>` : ''}
                ${summary.cointegration_coeff ? `<p><strong>协整系数：</strong>${summary.cointegration_coeff.toFixed(4)}</p>` : ''}
                ${summary.correlation_mean ? `<p><strong>动态相关系数均值：</strong>${summary.correlation_mean.toFixed(4)}</p>` : ''}
            </div>
        `;
    }

    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    console.log('分析结果已显示:', result);
}


/**
 * 重置分析
 */
function resetAnalysis() {
    // 隐藏结果区域
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }

    // 滚动回模型选择区域
    const modelSelection = document.getElementById('modelSelection');
    if (modelSelection) {
        modelSelection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    showInfo('已重置，可以重新选择模型运行');
}


// 导出全局函数供其他模块使用
window.GARCHApp = {
    uploadedFile,
    selectedSheet,
    columnMapping,
    showError,
    showSuccess,
    showInfo,
    generateReport,
    displayResult
};
