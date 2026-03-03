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
        console.log('文件上传成功:', result);

        // 显示工作表选择（displaySheets函数将在Task 4中实现）
        if (typeof displaySheets === 'function') {
            displaySheets(result.sheets, result.recommended_sheet);
        } else {
            console.log('工作表信息:', result.sheets);
            console.log('推荐工作表:', result.recommended_sheet);
            alert(`文件上传成功！\n\n文件名: ${result.filename}\n工作表数量: ${result.sheets.length}\n推荐工作表: ${result.recommended_sheet}\n\n（工作表显示功能将在下一步实现）`);
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

// 导出全局函数供其他模块使用
window.GARCHApp = {
    uploadedFile,
    selectedSheet,
    columnMapping,
    showError,
    showSuccess,
    showInfo
};
