import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  DatePicker,
  Upload,
  Button,
  Alert,
  Progress,
  message,
  Modal,
} from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useUpload } from '../api/hooks';
import type { UploadFile, RcFile } from 'antd/es/upload/interface';
import type { Dayjs } from 'dayjs';

const { Dragger } = Upload;
const { TextArea } = Input;

// 支持的音频/视频格式（由 ASR API 决定）
const supportedFormats: string[] = [
  'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/wave', 'audio/x-wav',
  'audio/m4a', 'audio/x-m4a', 'audio/ogg', 'audio/flac', 'audio/x-flac',
  'audio/aac', 'audio/x-aac', 'audio/opus', 'audio/webm', 'audio/amr',
  'audio/mp4', 'audio/x-ms-wma', 'audio/vnd.wave',
  'video/mp4', 'video/webm', 'video/x-matroska', 'video/x-flv',
  'video/mp2t', 'video/quicktime', 'video/x-msvideo',
];
const supportedExtensions: string[] = [
  '.3gp', '.3g2', '.8svx', '.aa', '.aac', '.aax', '.ac3', '.act', '.adp', '.adts',
  '.adx', '.aif', '.aiff', '.amr', '.ape', '.asf', '.ast', '.au', '.avr', '.caf',
  '.cda', '.dff', '.dsf', '.dsm', '.dss', '.dts', '.eac3', '.ec3', '.f32', '.f64',
  '.fap', '.flac', '.flv', '.gsm', '.ircam', '.m2ts', '.m4a', '.m4b', '.m4r',
  '.mka', '.mkv', '.mp2', '.mp3', '.mp4', '.mpc', '.mpp', '.mts', '.nut', '.nsv',
  '.oga', '.ogg', '.oma', '.opus', '.qcp', '.ra', '.ram', '.rm', '.sln', '.smp',
  '.snd', '.sox', '.spx', '.tak', '.tta', '.voc', '.w64', '.wav', '.wave', '.webm',
  '.wma', '.wve', '.wv', '.xa', '.xwma',
];

// 最大文件大小 500MB
const MAX_FILE_SIZE: number = 500 * 1024 * 1024;

// 表单值类型
interface FormValues {
  title: string;
  date?: Dayjs;
  participants?: string;
}

export default function UploadPage(): React.ReactElement {
  const navigate = useNavigate();
  const [form] = Form.useForm<FormValues>();
  const [file, setFile] = useState<File | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [estimatedTime, setEstimatedTime] = useState<string>('');
  const audioRef = useRef<HTMLAudioElement>(null);
  
  const { uploading, progress, upload } = useUpload();

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k: number = 1024;
    const sizes: string[] = ['B', 'KB', 'MB', 'GB'];
    const i: number = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 验证文件类型
  const validateFileType = (fileToValidate: RcFile): boolean => {
    const fileExtension: string = '.' + fileToValidate.name.split('.').pop()?.toLowerCase() || '';
    const isValidExtension: boolean = supportedExtensions.includes(fileExtension);
    const isValidType: boolean = supportedFormats.includes(fileToValidate.type) || isValidExtension;
    
    if (!isValidType) {
      message.error('不支持的文件格式，请上传常见音频或视频格式文件（如 MP3、WAV、AAC、FLAC、OGG、M4A、MP4、MKV 等）');
      return false;
    }
    return true;
  };

  // 验证文件大小
  const validateFileSize = (fileToValidate: RcFile): boolean => {
    if (fileToValidate.size > MAX_FILE_SIZE) {
      message.error('文件大小超过 500MB 限制');
      return false;
    }
    return true;
  };

  // 估算处理时间
  const estimateProcessingTime = (fileToEstimate: File): void => {
    try {
      const audio: HTMLAudioElement = new Audio();
      const url: string = URL.createObjectURL(fileToEstimate);
      audio.src = url;
      
      audio.onloadedmetadata = (): void => {
        const duration: number = audio.duration;
        URL.revokeObjectURL(url);
        
        const estimatedMinutes: number = Math.ceil((duration / 60) * 1.5);
        
        if (estimatedMinutes < 1) {
          setEstimatedTime('约30秒');
        } else if (estimatedMinutes < 60) {
          setEstimatedTime(`约${Math.ceil(estimatedMinutes)}分钟`);
        } else {
          const hours: number = Math.floor(estimatedMinutes / 60);
          const minutes: number = Math.ceil(estimatedMinutes % 60);
          setEstimatedTime(`约${hours}小时${minutes > 0 ? minutes + '分钟' : ''}`);
        }
      };
      
      audio.onerror = (): void => {
        URL.revokeObjectURL(url);
        setEstimatedTime('数分钟');
      };
    } catch (error) {
      console.error('估算处理时间失败:', error);
      setEstimatedTime('数分钟');
    }
  };

  // 文件变化处理
  const handleFileChange = (info: { fileList: UploadFile[] }): void => {
    const { fileList: newFileList } = info;
    setFileList(newFileList);
    
    if (newFileList.length > 0) {
      const selectedFile: UploadFile = newFileList[newFileList.length - 1];
      const rawFile: RcFile = (selectedFile.originFileObj || selectedFile) as RcFile;
      
      if (!validateFileType(rawFile)) {
        setFileList([]);
        return;
      }
      
      if (!validateFileSize(rawFile)) {
        setFileList([]);
        return;
      }
      
      setFile(rawFile);
      
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      
      const newAudioUrl: string = URL.createObjectURL(rawFile);
      setAudioUrl(newAudioUrl);
      
      estimateProcessingTime(rawFile);
    } else {
      setFile(null);
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl('');
      }
      setEstimatedTime('');
    }
  };

  // 重置表单
  const handleReset = (): void => {
    form.resetFields();
    setFile(null);
    setFileList([]);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl('');
    }
    setEstimatedTime('');
  };

  // 上传确认
  const handleUploadConfirm = async (): Promise<void> => {
    try {
      await form.validateFields();
    } catch (error) {
      return;
    }
    
    if (!file) {
      message.error('请选择要上传的音频文件');
      return;
    }
    
    Modal.confirm({
      title: '确认上传',
      content: '确认上传该音频文件？上传后将开始自动处理。',
      onOk: () => handleUpload(),
    });
  };

  // 执行上传
  const handleUpload = async (): Promise<void> => {
    try {
      const values: FormValues = await form.validateFields();
      
      const formData: FormData = new FormData();
      formData.append('audio', file as Blob);
      formData.append('title', values.title);
      if (values.date) {
        formData.append('date', values.date.format('YYYY-MM-DD'));
      }
      if (values.participants) {
        formData.append('participants', values.participants);
      }
      
      const result = await upload(formData);
      
      message.success('上传成功！');
      
      if (result.meeting_id) {
        navigate(`/meeting/${result.meeting_id}`);
      } else {
        navigate('/meetings');
      }
    } catch (error) {
      message.error((error as Error).message || '上传失败，请重试');
    }
  };

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  return (
    <div style={{ padding: 20, maxWidth: 800, margin: '0 auto' }}>
      <Card
        title="上传会议音频"
        style={{ borderRadius: 8 }}
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 20 }}
        >
          <Form.Item
            label="会议标题"
            name="title"
            rules={[
              { required: true, message: '请输入会议标题' },
              { min: 2, max: 100, message: '标题长度在 2 到 100 个字符' },
            ]}
          >
            <Input placeholder="请输入会议标题" maxLength={100} showCount />
          </Form.Item>

          <Form.Item label="会议日期" name="date">
            <DatePicker
              style={{ width: '100%' }}
              placeholder="选择会议日期"
              format="YYYY-MM-DD"
            />
          </Form.Item>

          <Form.Item label="参会人员" name="participants">
            <TextArea
              rows={2}
              placeholder="请输入参会人员，多个人员用逗号分隔"
            />
          </Form.Item>

          <Form.Item label="音频文件">
            <Dragger
              fileList={fileList}
              onChange={handleFileChange}
              beforeUpload={() => false}
              accept={supportedExtensions.join(',')}
              multiple={false}
              maxCount={1}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                将音频文件拖到此处，或<em>点击上传</em>
              </p>
              <p className="ant-upload-hint">
                支持 MP3、WAV、M4A、OGG、FLAC 格式，文件大小不超过 500MB
              </p>
            </Dragger>
          </Form.Item>

          {file && (
            <div style={{ marginBottom: 20 }}>
              <Alert
                message={`已选择文件: ${file.name}`}
                description={`文件大小: ${formatFileSize(file.size)}`}
                type="info"
                showIcon
                closable={false}
              />
            </div>
          )}

          {audioUrl && (
            <div style={{ marginBottom: 20, padding: 15, backgroundColor: '#f5f7fa', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: 14, color: '#606266' }}>音频预览</h4>
              <audio src={audioUrl} controls style={{ width: '100%' }} ref={audioRef} />
            </div>
          )}

          {progress > 0 && (
            <div style={{ marginBottom: 20 }}>
              <Progress
                percent={progress}
                status={progress === 100 ? 'success' : undefined}
              />
              <div style={{ textAlign: 'center', marginTop: 10, fontSize: 14, color: progress === 100 ? '#67c23a' : '#606266' }}>
                {progress < 100 ? `正在上传... ${progress}%` : '上传成功！正在处理中...'}
              </div>
            </div>
          )}

          {estimatedTime && (
            <div style={{ marginBottom: 20 }}>
              <Alert
                message="预计处理时间"
                description={`根据音频时长，预计需要 ${estimatedTime} 完成处理`}
                type="warning"
                showIcon
                closable={false}
              />
            </div>
          )}

          <Form.Item style={{ marginTop: 30, textAlign: 'center' }}>
            <Button onClick={handleReset} style={{ marginRight: 10 }}>
              重置
            </Button>
            <Button
              type="primary"
              loading={uploading}
              disabled={!file || progress > 0}
              onClick={handleUploadConfirm}
            >
              {uploading ? '上传中...' : '开始上传'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
