import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import type {
  BaseResponse,
  UploadResponseData,
  MeetingListResponseData,
  MeetingResponseData,
  StatusResponseData,
  ApiError
} from '../types';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 300000, // 5分钟超时（用于处理大文件上传）
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // 如果是上传文件，不设置 Content-Type，让浏览器自动设置
    if (config.data instanceof FormData) {
      delete config.headers?.['Content-Type'];
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse<BaseResponse | unknown>) => {
    const res = response.data as BaseResponse;
    // 如果后端返回的 code 不为 0，则视为错误
    if (res.code !== 0 && res.code !== undefined) {
      const error = new Error(res.message || '请求失败') as ApiError;
      error.code = res.code;
      error.data = (res as { data?: unknown }).data;
      return Promise.reject(error);
    }
    return (res as { data?: unknown }).data || res;
  },
  (error: AxiosError) => {
    let errorMessage = '网络错误，请稍后重试';
    const customError = new Error(errorMessage) as ApiError;
    customError.originalError = error;
    
    if (error.response) {
      const { status, data } = error.response;
      customError.status = status;
      customError.data = data;
      
      switch (status) {
        case 400:
          errorMessage = (data as { message?: string })?.message || '请求参数错误';
          break;
        case 401:
          errorMessage = '未授权，请重新登录';
          break;
        case 403:
          errorMessage = '拒绝访问';
          break;
        case 404:
          errorMessage = '请求的资源不存在';
          break;
        case 500:
          errorMessage = (data as { message?: string })?.message || '服务器内部错误';
          break;
        default:
          errorMessage = (data as { message?: string })?.message || `请求失败 (${status})`;
      }
    } else if (error.request) {
      errorMessage = '网络连接失败，请检查网络设置';
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    customError.message = errorMessage;
    return Promise.reject(customError);
  }
);

/**
 * 上传进度回调类型
 */
export type UploadProgressCallback = (percentCompleted: number) => void;

/**
 * API 接口封装
 */
export const api = {
  /**
   * 上传会议音频
   * @param formData - 包含 audio, title, date, participants 的 FormData
   * @param onUploadProgress - 上传进度回调函数
   * @returns 返回上传结果
   */
  uploadMeeting(
    formData: FormData, 
    onUploadProgress?: UploadProgressCallback
  ): Promise<UploadResponseData> {
    return apiClient.post('/meetings/upload', formData, {
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && progressEvent.total > 0 && onUploadProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percentCompleted);
        }
      },
    });
  },

  /**
   * 获取会议列表
   * @returns 返回会议列表
   */
  getMeetingList(): Promise<MeetingListResponseData> {
    return apiClient.get('/meetings');
  },

  /**
   * 获取会议详情
   * @param meetingId - 会议ID
   * @returns 返回会议详情
   */
  getMeeting(meetingId: string): Promise<MeetingResponseData> {
    return apiClient.get(`/meetings/${meetingId}`);
  },

  /**
   * 获取会议状态
   * @param meetingId - 会议ID
   * @returns 返回会议状态
   */
  getMeetingStatus(meetingId: string): Promise<StatusResponseData> {
    return apiClient.get(`/meetings/${meetingId}/status`);
  },

  /**
   * 获取会议纪要
   * @param meetingId - 会议ID
   * @returns 返回会议纪要
   */
  getMeetingSummary(meetingId: string): Promise<string> {
    return apiClient.get(`/meetings/${meetingId}/summary`);
  },

  /**
   * 删除会议
   * @param meetingId - 会议ID
   * @returns 返回删除结果
   */
  deleteMeeting(meetingId: string): Promise<void> {
    return apiClient.delete(`/meetings/${meetingId}`);
  },
};

export default apiClient;
