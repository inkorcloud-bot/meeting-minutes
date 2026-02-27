<template>
  <div class="meeting-detail-container">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-container">
      <el-icon class="is-loading"><loading /></el-icon>
      <span>加载中...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="errorMessage && !meeting" class="error-container">
      <el-card>
        <el-result
          icon="error"
          title="加载失败"
          :sub-title="errorMessage"
        >
          <template #extra>
            <el-button type="primary" @click="loadMeeting">
              重试
            </el-button>
            <el-button @click="goBack">
              返回列表
            </el-button>
          </template>
        </el-result>
      </el-card>
    </div>
    
    <!-- 详情内容 -->
    <div v-else-if="meeting" class="detail-content">
      <!-- 返回按钮 -->
      <div class="back-button">
        <el-button @click="goBack">
          <el-icon><arrow-left /></el-icon>
          返回列表
        </el-button>
      </div>
      
      <!-- 顶部卡片 -->
      <el-card class="header-card">
        <div class="header-content">
          <div class="title-section">
            <h1 class="meeting-title">{{ meeting.title }}</h1>
            <div class="meeting-meta">
              <span class="meta-item">
                <el-icon><calendar /></el-icon>
                {{ formatDate(meeting.created_at) }}
              </span>
              <el-tag :type="getStatusType(meeting.status)" size="large">
                {{ getStatusText(meeting.status) }}
              </el-tag>
            </div>
          </div>
          
          <div class="action-section">
            <el-button @click="refresh" :loading="isRefreshing">
              <el-icon><refresh /></el-icon>
              刷新
            </el-button>
            <el-popconfirm
              title="确定要删除这个会议吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete"
            >
              <template #reference>
                <el-button type="danger">
                  <el-icon><delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
        
        <!-- 进度条 -->
        <div v-if="meeting.status !== 'completed' && meeting.status !== 'failed'" class="progress-section">
          <div class="progress-header">
            <span>处理进度</span>
            <span class="progress-percentage">{{ meeting.progress }}%</span>
          </div>
          <el-progress
            :percentage="meeting.progress"
            :status="getProgressStatus(meeting.status)"
            :stroke-width="8"
          />
          <div v-if="meeting.current_step" class="current-step">
            当前步骤: {{ getStepText(meeting.current_step) }}
          </div>
        </div>
        
        <!-- 错误信息 -->
        <el-alert
          v-if="meeting.status === 'failed' && meeting.error"
          :title="meeting.error"
          type="error"
          :closable="false"
          class="error-alert"
        >
          <template #default>
            <div class="error-actions">
              <el-button type="primary" size="small" @click="goToUpload">
                重新上传
              </el-button>
            </div>
          </template>
        </el-alert>
      </el-card>
      
      <!-- 处理中提示 -->
      <div v-if="isProcessing" class="processing-notice">
        <el-alert
          title="正在后台处理中..."
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <div class="notice-content">
              <el-icon class="is-loading"><loading /></el-icon>
              <span>页面会自动刷新以显示最新进度</span>
            </div>
          </template>
        </el-alert>
      </div>
      
      <!-- 转录内容 -->
      <el-card v-if="meeting.transcript" class="transcript-card">
        <template #header>
          <div class="card-header">
            <el-icon><document /></el-icon>
            <span>原始转录</span>
          </div>
        </template>
        <div class="transcript-content">
          {{ meeting.transcript }}
        </div>
      </el-card>
      
      <!-- 会议纪要 -->
      <el-card v-if="meeting.summary" class="summary-card">
        <template #header>
          <div class="card-header">
            <el-icon><document-copy /></el-icon>
            <span>会议纪要</span>
            <div class="header-actions">
              <el-button type="primary" size="small" @click="copySummary">
                <el-icon><copy-document /></el-icon>
                复制
              </el-button>
            </div>
          </div>
        </template>
        <div class="summary-content" v-html="renderedSummary"></div>
      </el-card>
      
      <!-- 暂无内容提示 -->
      <div v-if="!meeting.transcript && !meeting.summary && !isProcessing" class="no-content">
        <el-empty description="暂无内容" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Loading,
  ArrowLeft,
  Refresh,
  Delete,
  Calendar,
  Document,
  DocumentCopy,
  CopyDocument
} from '@element-plus/icons-vue';
import { marked } from 'marked';
import {
  getMeeting,
  deleteMeeting,
  getUserFriendlyError
} from '../api';

const router = useRouter();
const route = useRoute();

// 状态
const meeting = ref(null);
const isLoading = ref(true);
const isRefreshing = ref(false);
const errorMessage = ref('');

// 轮询定时器
let pollTimer = null;

// 计算属性
const isProcessing = computed(() => {
  if (!meeting.value) return false;
  return ['uploaded', 'processing', 'transcribing', 'summarizing'].includes(meeting.value.status);
});

const renderedSummary = computed(() => {
  if (!meeting.value || !meeting.value.summary) return '';
  return marked(meeting.value.summary);
});

// 状态映射
const statusTypeMap = {
  uploaded: 'info',
  processing: 'primary',
  transcribing: 'warning',
  summarizing: 'warning',
  completed: 'success',
  failed: 'danger'
};

const statusTextMap = {
  uploaded: '等待处理',
  processing: '处理中',
  transcribing: '转录中',
  summarizing: '生成摘要中',
  completed: '已完成',
  failed: '失败'
};

const stepTextMap = {
  initializing: '初始化',
  transcribing: '语音识别',
  transcribed: '转录完成',
  summarizing: '生成摘要',
  completed: '已完成',
  error: '错误'
};

// 获取状态类型
const getStatusType = (status) => {
  return statusTypeMap[status] || 'info';
};

// 获取状态文本
const getStatusText = (status) => {
  return statusTextMap[status] || status;
};

// 获取进度状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'exception';
  return undefined;
};

// 获取步骤文本
const getStepText = (step) => {
  return stepTextMap[step] || step;
};

// 格式化日期
const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 加载会议详情
const loadMeeting = async (showLoading = true) => {
  if (showLoading) {
    isLoading.value = true;
  }
  isRefreshing.value = !showLoading;
  errorMessage.value = '';
  
  try {
    const meetingId = route.params.id;
    const result = await getMeeting(meetingId);
    
    if (result.data) {
      meeting.value = result.data;
    }
  } catch (error) {
    console.error('Failed to load meeting:', error);
    errorMessage.value = getUserFriendlyError(error);
  } finally {
    isLoading.value = false;
    isRefreshing.value = false;
  }
};

// 刷新
const refresh = () => {
  loadMeeting(false);
};

// 复制摘要
const copySummary = async () => {
  if (!meeting.value || !meeting.value.summary) return;
  
  try {
    await navigator.clipboard.writeText(meeting.value.summary);
    ElMessage.success('已复制到剪贴板');
  } catch (error) {
    console.error('Failed to copy:', error);
    ElMessage.error('复制失败，请手动复制');
  }
};

// 删除会议
const handleDelete = async () => {
  if (!meeting.value) return;
  
  try {
    await deleteMeeting(meeting.value.id);
    ElMessage.success('删除成功');
    goBack();
  } catch (error) {
    console.error('Failed to delete meeting:', error);
    ElMessage.error(getUserFriendlyError(error));
  }
};

// 返回列表
const goBack = () => {
  router.push('/meetings');
};

// 跳转到上传页面
const goToUpload = () => {
  router.push('/upload');
};

// 启动轮询
const startPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  
  pollTimer = setInterval(() => {
    if (isProcessing.value) {
      loadMeeting(false);
    }
  }, 3000); // 每 3 秒轮询一次
};

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

// 监听处理状态变化
watch(isProcessing, (newValue) => {
  if (newValue) {
    startPolling();
  } else {
    stopPolling();
  }
});

// 生命周期
onMounted(() => {
  loadMeeting();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.meeting-detail-container {
  max-width: 1000px;
  margin: 40px auto;
  padding: 0 20px;
}

.loading-container,
.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 600px;
}

.loading-container {
  gap: 10px;
  color: #909399;
}

.loading-container .el-icon {
  font-size: 24px;
}

.back-button {
  margin-bottom: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 20px;
}

.title-section {
  flex: 1;
}

.meeting-title {
  margin: 0 0 10px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.meeting-meta {
  display: flex;
  align-items: center;
  gap: 15px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
}

.meta-item .el-icon {
  font-size: 16px;
}

.action-section {
  display: flex;
  gap: 10px;
}

.progress-section {
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
}

.progress-percentage {
  font-weight: 600;
  color: #409eff;
}

.current-step {
  margin-top: 10px;
  font-size: 13px;
  color: #909399;
}

.error-alert {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #fde2e2;
}

.error-actions {
  margin-top: 10px;
}

.processing-notice {
  margin-bottom: 20px;
}

.notice-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.notice-content .el-icon {
  font-size: 18px;
}

.transcript-card,
.summary-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.card-header .el-icon {
  font-size: 20px;
  color: #409eff;
}

.header-actions {
  margin-left: auto;
}

.transcript-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
}

.summary-content {
  padding: 10px 0;
  line-height: 1.8;
}

/* Markdown 样式 */
.summary-content :deep(h1) {
  font-size: 24px;
  margin: 20px 0 15px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #409eff;
  color: #303133;
}

.summary-content :deep(h2) {
  font-size: 20px;
  margin: 20px 0 12px 0;
  color: #409eff;
}

.summary-content :deep(h3) {
  font-size: 18px;
  margin: 15px 0 10px 0;
  color: #606266;
}

.summary-content :deep(p) {
  margin: 10px 0;
  color: #606266;
}

.summary-content :deep(ul),
.summary-content :deep(ol) {
  margin: 10px 0;
  padding-left: 25px;
}

.summary-content :deep(li) {
  margin: 5px 0;
  color: #606266;
}

.summary-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0;
}

.summary-content :deep(th),
.summary-content :deep(td) {
  border: 1px solid #ebeef5;
  padding: 10px 15px;
  text-align: left;
}

.summary-content :deep(th) {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.summary-content :deep(td) {
  color: #606266;
}

.no-content {
  padding: 60px 0;
}
</style>
