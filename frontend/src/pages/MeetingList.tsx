import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Progress,
  Modal,
  message,
  Pagination,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useMeetingList } from '../api/hooks';
import { api } from '../api';
import type { MeetingListItem } from '../types';
import type { ColumnsType } from 'antd/es/table';

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

// 表格行类型
interface TableRow extends MeetingListItem {
  key: string;
}

export default function MeetingList(): React.ReactElement {
  const navigate = useNavigate();
  const { meetings, loading, error, refresh } = useMeetingList();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [deleteModalVisible, setDeleteModalVisible] = useState<boolean>(false);
  const [meetingToDelete, setMeetingToDelete] = useState<MeetingListItem | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  // 格式化日期
  const formatDate = (dateStr: string): string => {
    if (!dateStr) return '-';
    const date: Date = new Date(dateStr);
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

  // 查看详情
  const viewDetail = (meeting: MeetingListItem): void => {
    navigate(`/meeting/${meeting.id}`);
  };

  // 处理删除按钮点击
  const handleDeleteClick = (meeting: MeetingListItem): void => {
    setMeetingToDelete(meeting);
    setDeleteModalVisible(true);
  };

  // 确认删除
  const confirmDelete = async (): Promise<void> => {
    if (!meetingToDelete) return;
    
    setDeleting(true);
    try {
      await api.deleteMeeting(meetingToDelete.id);
      message.success('删除成功');
      setDeleteModalVisible(false);
      await refresh();
    } catch (err) {
      message.error((err as Error).message || '删除失败');
    } finally {
      setDeleting(false);
    }
  };

  // 排序会议列表（按创建时间倒序）
  const sortedMeetings: MeetingListItem[] = [...meetings].sort((a: MeetingListItem, b: MeetingListItem) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  // 分页数据
  const paginatedMeetings: TableRow[] = sortedMeetings.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  ).map((meeting: MeetingListItem) => ({
    ...meeting,
    key: meeting.id,
  }));

  // 表格列定义
  const columns: ColumnsType<TableRow> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      minWidth: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusType(status)} size="small">
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 200,
      render: (progress: number, record: TableRow) => (
        <div>
          <Progress
            percent={progress}
            status={record.status === 'error' ? 'exception' : undefined}
            size={["100%", 8]}
          />
          {record.current_step && (
            <div style={{ fontSize: 12, color: '#909399', marginTop: 4, textAlign: 'center' }}>
              {getStepText(record.current_step as string)}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDate(date),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_: unknown, record: TableRow) => (
        <>
          <Button
            type="primary"
            size="small"
            onClick={() => viewDetail(record)}
            style={{ marginRight: 8 }}
          >
            查看详情
          </Button>
          <Button
            type="default"
            danger
            size="small"
            onClick={() => handleDeleteClick(record)}
          >
            删除
          </Button>
        </>
      ),
    },
  ];

  // 自动刷新（每5秒）
  useEffect(() => {
    const timer: NodeJS.Timeout = setInterval(() => {
      refresh();
    }, 5000);

    return () => {
      clearInterval(timer);
    };
  }, [refresh]);

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>会议列表</h2>
        <Button type="primary" onClick={refresh} icon={<ReloadOutlined />}>
          刷新
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={paginatedMeetings}
        rowKey="id"
        loading={loading}
        pagination={false}
        stripe
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
        <Pagination
          current={currentPage}
          pageSize={pageSize}
          pageSizeOptions={['10', '20', '50', '100']}
          total={sortedMeetings.length}
          showSizeChanger
          showTotal={(total: number) => `共 ${total} 条`}
          onChange={(page: number, size: number) => {
            setCurrentPage(page);
            setPageSize(size);
          }}
          onShowSizeChange={(_current: number, size: number) => {
            setCurrentPage(1);
            setPageSize(size);
          }}
        />
      </div>

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
        <p>确定要删除会议「{meetingToDelete?.title}」吗？此操作不可恢复。</p>
      </Modal>
    </div>
  );
}
