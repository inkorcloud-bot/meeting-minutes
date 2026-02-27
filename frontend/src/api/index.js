/**
 * API 客户端模块
 * 
 * 提供统一的 API 请求封装和错误处理
 */

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

// 请求超时时间（毫秒）
const DEFAULT_TIMEOUT = 30000; // 30 秒

/**
 * API 错误类
 */
export class ApiError extends Error {
  constructor(message, code, statusCode) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

/**
 * 网络错误类
 */
export class NetworkError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * 获取用户友好的错误信息
 * @param {Error} error - 错误对象
 * @returns {string} 用户友好的错误信息
 */
export function getUserFriendlyError(error) {
  if (error instanceof ApiError) {
    return error.message;
  }
  
  if (error instanceof NetworkError) {
    return '网络连接失败，请检查网络后重试';
  }
  
  if (error.name === 'AbortError') {
    return '请求超时，请稍后重试';
  }
  
  if (error.message && error.message.includes('fetch')) {
    return '无法连接到服务器，请稍后重试';
  }
  
  return error.message || '操作失败，请稍后重试';
}

/**
 * 统一的请求函数
 * @param {string} endpoint - API 端点
 * @param {object} options - 请求选项
 * @returns {Promise<any>} 响应数据
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    clearTimeout(timeoutId);
    
    const data = await response.json().catch(() => null);
    
    if (!response.ok) {
      if (data && data.message) {
        throw new ApiError(
          data.message,
          data.code || response.status,
          response.status
        );
      }
      throw new ApiError(
        `请求失败: ${response.status} ${response.statusText}`,
        response.status,
        response.status
      );
    }
    
    if (data && data.code !== 0 && data.code !== undefined) {
      throw new ApiError(
        data.message || '操作失败',
        data.code,
        response.status
      );
    }
    
    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      throw error;
    }
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    if (error.message && error.message.includes('fetch')) {
      throw new NetworkError('网络连接失败');
    }
    
    throw error;
  }
}

/**
 * GET 请求
 * @param {string} endpoint - API 端点
 * @param {object} options - 请求选项
 * @returns {Promise<any>} 响应数据
 */
export async function get(endpoint, options = {}) {
  return request(endpoint, {
    ...options,
    method: 'GET',
  });
}

/**
 * POST 请求
 * @param {string} endpoint - API 端点
 * @param {any} body - 请求体
 * @param {object} options - 请求选项
 * @returns {Promise<any>} 响应数据
 */
export async function post(endpoint, body, options = {}) {
  return request(endpoint, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE 请求
 * @param {string} endpoint - API 端点
 * @param {object} options - 请求选项
 * @returns {Promise<any>} 响应数据
 */
export async function del(endpoint, options = {}) {
  return request(endpoint, {
    ...options,
    method: 'DELETE',
  });
}

/**
 * 上传文件
 * @param {string} endpoint - API 端点
 * @param {FormData} formData - 表单数据
 * @param {object} options - 请求选项
 * @param {Function} onProgress - 进度回调
 * @returns {Promise<any>} 响应数据
 */
export async function upload(endpoint, formData, options = {}, onProgress) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const xhr = new XMLHttpRequest();
  
  return new Promise((resolve, reject) => {
    xhr.open('POST', url);
    
    // 设置超时
    xhr.timeout = options.timeout || 5 * 60 * 1000; // 默认 5 分钟
    
    // 进度回调
    if (onProgress && xhr.upload) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = Math.round((e.loaded / e.total) * 100);
          onProgress(progress);
        }
      });
    }
    
    xhr.addEventListener('load', () => {
      try {
        const data = JSON.parse(xhr.responseText);
        
        if (xhr.status >= 200 && xhr.status < 300) {
          if (data.code !== 0 && data.code !== undefined) {
            reject(new ApiError(
              data.message || '上传失败',
              data.code,
              xhr.status
            ));
          } else {
            resolve(data);
          }
        } else {
          if (data && data.message) {
            reject(new ApiError(data.message, data.code, xhr.status));
          } else {
            reject(new ApiError(
              `上传失败: ${xhr.status} ${xhr.statusText}`,
              xhr.status,
              xhr.status
            ));
          }
        }
      } catch (e) {
        reject(new ApiError('响应解析失败', xhr.status, xhr.status));
      }
    });
    
    xhr.addEventListener('error', () => {
      reject(new NetworkError('网络连接失败'));
    });
    
    xhr.addEventListener('timeout', () => {
      reject(new Error('上传超时，请稍后重试'));
    });
    
    xhr.send(formData);
  });
}

// ========== 会议相关 API ==========

/**
 * 上传会议音频
 * @param {File} audioFile - 音频文件
 * @param {string} title - 会议标题
 * @param {string} date - 会议日期（可选）
 * @param {string} participants - 参会人员（可选）
 * @param {Function} onProgress - 进度回调
 * @returns {Promise<object>} 上传结果
 */
export async function uploadMeeting(
  audioFile,
  title,
  date = '',
  participants = '',
  onProgress
) {
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('title', title);
  if (date) formData.append('date', date);
  if (participants) formData.append('participants', participants);
  
  return upload('/api/v1/meetings/upload', formData, {}, onProgress);
}

/**
 * 获取会议列表
 * @param {number} skip - 跳过数量
 * @param {number} limit - 返回数量限制
 * @param {string} status - 状态过滤（可选）
 * @returns {Promise<object>} 会议列表
 */
export async function getMeetings(skip = 0, limit = 100, status = '') {
  let endpoint = `/api/v1/meetings?skip=${skip}&limit=${limit}`;
  if (status) {
    endpoint += `&status=${encodeURIComponent(status)}`;
  }
  return get(endpoint);
}

/**
 * 获取会议详情
 * @param {string} meetingId - 会议ID
 * @returns {Promise<object>} 会议详情
 */
export async function getMeeting(meetingId) {
  return get(`/api/v1/meetings/${meetingId}`);
}

/**
 * 获取会议状态
 * @param {string} meetingId - 会议ID
 * @returns {Promise<object>} 会议状态
 */
export async function getMeetingStatus(meetingId) {
  return get(`/api/v1/meetings/${meetingId}/status`);
}

/**
 * 获取会议纪要
 * @param {string} meetingId - 会议ID
 * @returns {Promise<object>} 会议纪要
 */
export async function getMeetingSummary(meetingId) {
  return get(`/api/v1/meetings/${meetingId}/summary`);
}

/**
 * 删除会议
 * @param {string} meetingId - 会议ID
 * @returns {Promise<object>} 删除结果
 */
export async function deleteMeeting(meetingId) {
  return del(`/api/v1/meetings/${meetingId}`);
}

/**
 * 重新生成会议纪要（流式 SSE）
 * @param {string} meetingId - 会议ID
 * @param {Function} onChunk - 每个内容片段的回调 (chunk: string) => void
 * @returns {Promise<string>} 完整的会议纪要
 */
export async function regenerateMeetingSummary(meetingId, onChunk) {
  const url = `${API_BASE_URL}/api/v1/meetings/${meetingId}/regenerate-summary`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 分钟超时

  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Accept': 'text/event-stream' },
      signal: controller.signal,
    });
  } catch (e) {
    clearTimeout(timeoutId);
    throw e;
  }

  if (!response.ok) {
    clearTimeout(timeoutId);
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      data.message || `请求失败: ${response.status}`,
      data.code || response.status,
      response.status
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullSummary = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6).replace(/\r$/, '').trim();
          if (!jsonStr) continue;
          try {
            const data = JSON.parse(jsonStr);
            if (data.error) {
              throw new ApiError(data.error, 500, 500);
            }
            if (data.chunk) {
              fullSummary += data.chunk;
              onChunk && onChunk(data.chunk);
            }
            if (data.done && data.summary !== undefined) {
              fullSummary = data.summary;
            }
          } catch (e) {
            if (e instanceof ApiError) throw e;
          }
        }
      }
    }

    if (buffer.startsWith('data: ')) {
      const jsonStr = buffer.slice(6).trim();
      if (jsonStr) {
        try {
          const data = JSON.parse(jsonStr);
          if (data.error) throw new ApiError(data.error, 500, 500);
          if (data.done && data.summary !== undefined) fullSummary = data.summary;
        } catch (e) {
          if (e instanceof ApiError) throw e;
        }
      }
    }

    return fullSummary;
  } finally {
    clearTimeout(timeoutId);
    reader.releaseLock();
  }
}

export default {
  API_BASE_URL,
  ApiError,
  NetworkError,
  getUserFriendlyError,
  get,
  post,
  del,
  upload,
  uploadMeeting,
  getMeetings,
  getMeeting,
  getMeetingStatus,
  getMeetingSummary,
  deleteMeeting,
  regenerateMeetingSummary,
};
