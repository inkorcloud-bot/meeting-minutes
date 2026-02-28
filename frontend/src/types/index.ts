// ========== 基础响应类型 ==========

export interface BaseResponse {
  code: number;
  message: string;
}

export interface DataResponse<T = unknown> extends BaseResponse {
  data?: T;
}

// ========== 上传相关类型 ==========

export interface UploadRequest {
  title: string;
  date?: string;
  participants?: string;
}

export interface UploadResponseData {
  meeting_id: string;
  status: string;
  estimated_processing_time?: string;
}

export interface UploadResponse extends BaseResponse {
  data: UploadResponseData;
}

// ========== 状态查询相关类型 ==========

export interface StatusResponseData {
  meeting_id: string;
  status: string;
  progress: number;
  current_step?: string;
  error?: string;
}

export interface StatusResponse extends BaseResponse {
  data: StatusResponseData;
}

// ========== 会议信息相关类型 ==========

export interface MeetingResponseData {
  id: string;
  title: string;
  status: string;
  audio_path?: string;
  audio_duration?: number;
  transcript?: string;
  summary?: string;
  progress: number;
  current_step?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface MeetingResponse extends BaseResponse {
  data: MeetingResponseData;
}

export interface MeetingListItem {
  id: string;
  title: string;
  status: string;
  progress: number;
  created_at: string;
}

export interface MeetingListResponseData {
  total: number;
  items: MeetingListItem[];
}

export interface MeetingListResponse extends BaseResponse {
  data: MeetingListResponseData;
}

// ========== 错误响应类型 ==========

export interface ErrorResponse extends BaseResponse {
  code: number;
  message: string;
}

// ========== 会议状态枚举 ==========

export type MeetingStatus = 
  | 'pending' 
  | 'uploading' 
  | 'uploaded' 
  | 'processing' 
  | 'transcribing' 
  | 'summarizing' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

// ========== API 错误类型 ==========

export interface ApiError extends Error {
  code?: number;
  status?: number;
  data?: unknown;
  originalError?: unknown;
}

// ========== Hooks 返回类型 ==========

export interface UseMeetingListReturn {
  meetings: MeetingListItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export interface UseMeetingReturn {
  meeting: MeetingResponseData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export interface UseMeetingStatusPollingReturn {
  status: StatusResponseData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export interface UseUploadReturn {
  uploading: boolean;
  progress: number;
  error: string | null;
  upload: (formData: FormData) => Promise<UploadResponseData>;
  reset: () => void;
}
