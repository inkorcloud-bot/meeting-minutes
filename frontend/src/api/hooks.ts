import { useState, useEffect, useCallback } from 'react';
import { api } from './index';
import type {
  MeetingListItem,
  MeetingResponseData,
  StatusResponseData,
  UploadResponseData,
  UseMeetingListReturn,
  UseMeetingReturn,
  UseMeetingStatusPollingReturn,
  UseUploadReturn
} from '../types';

/**
 * 使用会议列表的 Hook
 */
export function useMeetingList(): UseMeetingListReturn {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMeetings = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMeetingList();
      setMeetings(data.items || []);
    } catch (err) {
      setError((err as Error).message || '获取会议列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  return {
    meetings,
    loading,
    error,
    refresh: fetchMeetings,
  };
}

/**
 * 使用会议详情的 Hook
 */
export function useMeeting(meetingId: string | null): UseMeetingReturn {
  const [meeting, setMeeting] = useState<MeetingResponseData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMeeting = useCallback(async (): Promise<void> => {
    if (!meetingId) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMeeting(meetingId);
      setMeeting(data);
    } catch (err) {
      setError((err as Error).message || '获取会议详情失败');
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  useEffect(() => {
    fetchMeeting();
  }, [fetchMeeting]);

  return {
    meeting,
    loading,
    error,
    refresh: fetchMeeting,
  };
}

/**
 * 使用会议状态轮询的 Hook
 */
export function useMeetingStatusPolling(
  meetingId: string | null, 
  interval: number = 3000
): UseMeetingStatusPollingReturn {
  const [status, setStatus] = useState<StatusResponseData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async (): Promise<void> => {
    if (!meetingId) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMeetingStatus(meetingId);
      setStatus(data);
    } catch (err) {
      setError((err as Error).message || '获取会议状态失败');
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  useEffect(() => {
    fetchStatus();
    
    // 如果状态不是终态，继续轮询
    const isTerminalStatus = (statusValue: string | undefined): boolean => {
      return statusValue === 'completed' || statusValue === 'failed' || statusValue === 'cancelled';
    };

    let timer: NodeJS.Timeout | null = null;
    if (!isTerminalStatus(status?.status)) {
      timer = setInterval(fetchStatus, interval);
    }

    return () => {
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [fetchStatus, status?.status, interval]);

  return {
    status,
    loading,
    error,
    refresh: fetchStatus,
  };
}

/**
 * 使用上传功能的 Hook
 */
export function useUpload(): UseUploadReturn {
  const [uploading, setUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (formData: FormData): Promise<UploadResponseData> => {
    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const result = await api.uploadMeeting(formData, (percent: number) => {
        setProgress(percent);
      });
      return result;
    } catch (err) {
      setError((err as Error).message || '上传失败');
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  const reset = useCallback((): void => {
    setProgress(0);
    setError(null);
  }, []);

  return {
    uploading,
    progress,
    error,
    upload,
    reset,
  };
}
