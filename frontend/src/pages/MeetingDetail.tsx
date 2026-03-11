import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Progress,
  Button,
  Alert,
  Modal,
  message,
  Skeleton,
  Result,
} from 'antd';
import {
  ArrowLeftOutlined,
  CopyOutlined,
  DeleteOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { marked } from 'marked';
import { useMeeting } from '../api/hooks';
import { api } from '../api';
import type { MeetingResponseData } from '../types';

// 状态配置
const statusConfig: Record<string, { type: string; text: string }> = {
  uploaded: { type: 'default', text: '已上传' },
  processing: { type: 'processing', text: '处理中' },
  transcribing: { type: 'warning', text: '转录中' },
  summarizing: { type: 'warning', text: '总结中' },
  're-summarizing': { type: 'processing', text: '重新生成摘要中' },
  completed: { type: 'success', text: '已完成' },
  error: { type: 'error', text: '错误' },
  failed: { type: 'error', text: '失败' },
};

// 步骤文本映射
const stepTextMap: Record<string, string> = {
  uploaded: '等待处理',
  processing: '准备处理',
  transcribing: '语音识别中',
  summarizing: '生成纪要中',
  're-summarizing': '重新生成摘要中',
  completed: '处理完成',
  error: '处理失败',
  failed: '处理失败',
};

// 扩展的会议类型（包含可选字段）
interface ExtendedMeeting extends MeetingResponseData {
  date?: string;
  participants?: string;
}

export default function MeetingDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { meeting, loading, error, refresh } = useMeeting(id || null);
  const [showTranscript, setShowTranscript] = useState<boolean>(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [regenerating, setRegenerating] = useState<boolean>(false);
  const [streamingSummary, setStreamingSummary] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 格式化日期
  const formatDate = (dateStr: string): string => {
    if (!dateStr) return '-';
    // 若字符串不含时区信息，补上 'Z' 以明确标识为 UTC，确保浏览器正确转换为本地时间
    const normalized = /[Z+]/.test(dateStr) ? dateStr : dateStr + 'Z';
    const date: Date = new Date(normalized);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 获取状态类型
  const getStatusType = (status: string): string => {
    return statusConfig[status]?.type || 'info';
  };

  // 获取状态文本
  const getStatusText = (status: string): string => {
    return statusConfig[status]?.text || status;
  };

  // 获取步骤文本
  const getStepText = (step: string): string => {
    return stepTextMap[step] || step;
  };

  // 返回列表
  const goBack = (): void => {
    navigate('/meetings');
  };

  // 切换转录显示
  const toggleTranscript = (): void => {
    setShowTranscript(!showTranscript);
  };

  // 复制纪要
  const copySummary = async (): Promise<void> => {
    if (!meeting?.summary) return;

    try {
      await navigator.clipboard.writeText(meeting.summary);
      message.success('已复制到剪贴板');
    } catch (err) {
      // 降级方案
      const textarea: HTMLTextAreaElement = document.createElement('textarea');
      textarea.value = meeting.summary;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      message.success('已复制到剪贴板');
    }
  };

  // 删除相关
  const handleDelete = (): void => {
    setDeleteModalVisible(true);
  };

  const confirmDelete = async (): Promise<void> => {
    if (!meeting) return;

    setDeleting(true);
    try {
      await api.deleteMeeting(meeting.id);
      message.success('删除成功');
      navigate('/meetings');
    } catch (err) {
      message.error((err as Error).message || '删除失败');
    } finally {
      setDeleting(false);
      setDeleteModalVisible(false);
    }
  };

  // 重新生成纪要
  const handleRegenerateSummary = (): void => {
    if (!meeting?.id) return;

    setRegenerating(true);
    setStreamingSummary('');

    abortControllerRef.current = api.regenerateSummary(
      meeting.id,
      (chunk) => {
        setStreamingSummary((prev) => (prev ?? '') + chunk);
      },
      (_summary) => {
        setRegenerating(false);
        setStreamingSummary(null);
        refresh();
        message.success('纪要重新生成成功');
      },
      (error) => {
        setRegenerating(false);
        setStreamingSummary(null);
        message.error(error || '重新生成失败');
      }
    );
  };

  // 取消重新生成
  const handleCancelRegenerate = (): void => {
    abortControllerRef.current?.abort();
    setRegenerating(false);
    setStreamingSummary(null);
  };

  // 如果还在处理中，定期刷新
  useEffect(() => {
    if (!meeting) return;

    if (['completed', 'error'].includes(meeting.status) && !regenerating) {
      return;
    }

    const timer: NodeJS.Timeout = setInterval(() => {
      refresh();
    }, 3000);

    return () => {
      clearInterval(timer);
    };
  }, [meeting?.status, regenerating, refresh]);

  // 渲染 Markdown
  const renderSummary = (content: string): React.ReactElement => {
    if (!content) return <></>;
    const html: string = marked.parse(content, { breaks: true }) as string;
    return <div className="markdown-content" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  const extendedMeeting: ExtendedMeeting | null = meeting ? {
    ...meeting,
    date: undefined,
    participants: undefined,
  } : null;

  if (loading) {
    return (
      <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20 }}>
          <Button onClick={goBack} icon={<ArrowLeftOutlined />}>返回列表</Button>
          <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>会议详情</h2>
        </div>
        <div style={{ padding: 20 }}>
          <Skeleton active paragraph={{ rows: 10 }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20 }}>
          <Button onClick={goBack} icon={<ArrowLeftOutlined />}>返回列表</Button>
          <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>会议详情</h2>
        </div>
        <div style={{ padding: '40px 0' }}>
          <Result
            status="error"
            title="加载失败"
            subTitle={error}
            extra={
              <Button type="primary" onClick={refresh}>重试</Button>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20 }}>
        <Button onClick={goBack} icon={<ArrowLeftOutlined />}>返回列表</Button>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
          {meeting?.title || '会议详情'}
        </h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* 基本信息卡片 */}
        <Card
          style={{ borderRadius: 8 }}
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>会议信息</span>
              {meeting && (
                <Tag color={getStatusType(meeting.status)}>
                  {getStatusText(meeting.status)}
                </Tag>
              )}
            </div>
          }
        >
          {meeting && (
            <Descriptions column={2} bordered>
              <Descriptions.Item label="会议标题">
                {meeting.title}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatDate(meeting.created_at)}
              </Descriptions.Item>
              {extendedMeeting?.date && (
                <Descriptions.Item label="会议日期">
                  {extendedMeeting.date}
                </Descriptions.Item>
              )}
              {extendedMeeting?.participants && (
                <Descriptions.Item label="参会人员">
                  {extendedMeeting.participants}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="处理进度" span={2}>
                <div style={{ width: '100%' }}>
                  <Progress
                    percent={meeting.progress}
                    status={meeting.status === 'error' ? 'exception' : undefined}
                    size={["100%", 20]}
                  />
                  {meeting.current_step && (
                    <div style={{ marginTop: 8, fontSize: 14, color: '#606266', textAlign: 'center' }}>
                      当前步骤：{getStepText(meeting.current_step)}
                    </div>
                  )}
                </div>
              </Descriptions.Item>
              {meeting.error && (
                <Descriptions.Item label="错误信息" span={2}>
                  <Alert
                    message={meeting.error}
                    type="error"
                    closable={false}
                    showIcon
                  />
                </Descriptions.Item>
              )}
            </Descriptions>
          )}
        </Card>

        {/* 会议纪要 */}
        {(meeting?.summary || regenerating) && (
          <Card
            style={{ borderRadius: 8 }}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>会议纪要{regenerating && <SyncOutlined spin style={{ marginLeft: 8, color: '#1677ff' }} />}</span>
                {!regenerating && meeting?.summary && (
                  <Button type="primary" size="small" onClick={copySummary} icon={<CopyOutlined />}>
                    复制纪要
                  </Button>
                )}
              </div>
            }
          >
            {regenerating && streamingSummary !== null ? (
              <div>
                {streamingSummary
                  ? renderSummary(streamingSummary)
                  : <div style={{ color: '#999', padding: '20px 0', textAlign: 'center' }}>正在生成纪要，请稍候...</div>
                }
              </div>
            ) : (
              renderSummary(meeting?.summary ?? '')
            )}
          </Card>
        )}

        {/* 原始转录（可选显示） */}
        {meeting?.transcript && showTranscript && (
          <Card
            style={{ borderRadius: 8 }}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>原始转录</span>
              </div>
            }
          >
            <div style={{
              maxHeight: 300,
              overflowY: 'auto',
              padding: 16,
              backgroundColor: '#f5f7fa',
              borderRadius: 4,
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
            }}>
              {meeting.transcript}
            </div>
          </Card>
        )}

        {/* 操作按钮 */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: 20,
          borderTop: '1px solid #eee',
        }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {meeting?.transcript && (
              <Button onClick={toggleTranscript}>
                {showTranscript ? '隐藏' : '显示'}原始转录
              </Button>
            )}
            {meeting?.transcript && !regenerating && (
              <Button
                icon={<SyncOutlined />}
                onClick={handleRegenerateSummary}
                disabled={['uploaded', 'processing', 'transcribing', 'summarizing'].includes(meeting.status)}
              >
                重新生成纪要
              </Button>
            )}
            {regenerating && (
              <Button onClick={handleCancelRegenerate}>
                取消生成
              </Button>
            )}
          </div>
          <Button type="primary" danger onClick={handleDelete} icon={<DeleteOutlined />} disabled={regenerating}>
            删除会议
          </Button>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <Modal
        title="确认删除"
        open={deleteModalVisible}
        onCancel={() => setDeleteModalVisible(false)}
        onOk={confirmDelete}
        confirmLoading={deleting}
        okText="删除"
        okType="danger"
        cancelText="取消"
        width={400}
      >
        <p>确定要删除会议「{meeting?.title}」吗？此操作不可恢复。</p>
      </Modal>
    </div>
  );
}
