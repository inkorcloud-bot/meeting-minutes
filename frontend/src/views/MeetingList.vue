<template>
  <div class="meeting-list-container">
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>会议列表</span>
          <el-button type="primary" @click="goToUpload">
            <el-icon><plus /></el-icon>
            上传新会议
          </el-button>
        </div>
      </template>
      
      <!-- 错误提示 -->
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="true"
        @close="errorMessage = ''"
        class="error-alert"
      />
      
      <!-- 筛选器 -->
      <div class="filter-bar">
        <el-select
          v-model="statusFilter"
          placeholder="按状态筛选"
          clearable
          @change="handleFilterChange"
          style="width: 200px"
        >
          <el-option label="全部" value="" />
          <el-option label="等待处理" value="uploaded" />
          <el-option label="处理中" value="processing" />
          <el-option label="转录中" value="transcribing" />
          <el-option label="生成摘要中" value="summarizing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        
        <el-button @click="refreshList" :loading="isLoading">
          <el-icon><refresh /></el-icon>
          刷新
        </el-button>
      </div>
      
      <!-- 加载状态 -->
      <div v-if="isLoading && meetings.length === 0" class="loading-container">
        <el-icon class="is-loading"><loading /></el-icon>
        <span>加载中...</span>
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="meetings.length === 0" class="empty-container">
        <el-empty description="暂无会议记录">
          <el-button type="primary" @click="goToUpload">
            上传第一个会议
          </el-button>
        </el-empty>
      </div>
      
      <!-- 会议列表 -->
      <div v-else class="meetings-grid">
        <el-card
          v-for="meeting in meetings"
          :key="meeting.id"
          class="meeting-card"
          shadow="hover"
          @click="goToDetail(meeting.id)"
        >
          <div class="meeting-header">
            <h3 class="meeting-title" :title="meeting.title">
              {{ meeting.title }}
            </h3>
            <el-tag :type="getStatusType(meeting.status)" size="small">
              {{ getStatusText(meeting.status) }}
            </el-tag>
          </div>
          
          <div class="meeting-info">
            <div class="info-item">
              <el-icon><calendar /></el-icon>
              <span>{{ formatDate(meeting.created_at) }}</span>
            </div>
            
            <div class="info-item" v-if="meeting.status !== 'completed' && meeting.status !== 'failed'">
              <el-icon><data-line /></el-icon>
              <span>进度: {{ meeting.progress }}%</span>
            </div>
          </div>
          
          <!-- 进度条 -->
          <el-progress
            v-if="meeting.status !== 'completed' && meeting.status !== 'failed'"
            :percentage="meeting.progress"
            :status="getProgressStatus(meeting.status)"
            :stroke-width="6"
            class="progress-bar"
          />
          
          <!-- 失败状态显示错误 -->
          <div v-if="meeting.status === 'failed'" class="error-info">
            <el-icon><warning-filled /></el-icon>
            <span class="error-text">处理失败</span>
          </div>
          
          <!-- 操作按钮 -->
          <div class="meeting-actions">
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="goToDetail(meeting.id)"
            >
              查看详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              link
              @click.stop="handleDelete(meeting)"
            >
              删除
            </el-button>
          </div>
        </el-card>
      </div>
      
      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Plus,
  Refresh,
  Loading,
  Calendar,
  DataLine,
  WarningFilled
} from '@element-plus/icons-vue';
import {
  getMeetings,
  deleteMeeting,
  getUserFriendlyError
} from '../api';

const router = useRouter();

// 状态
const meetings = ref([]);
const total = ref(0);
const isLoading = ref(false);
const errorMessage = ref('');
const statusFilter = ref('');
const currentPage = ref(1);
const pageSize = ref(20);

// 轮询定时器
let pollTimer = null;

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

// 格式化日期
const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 加载会议列表
const loadMeetings = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  
  try {
    const skip = (currentPage.value - 1) * pageSize.value;
    const result = await getMeetings(skip, pageSize.value, statusFilter.value);
    
    if (result.data) {
      meetings.value = result.data.items || [];
      total.value = result.data.total || 0;
    }
  } catch (error) {
    console.error('Failed to load meetings:', error);
    errorMessage.value = getUserFriendlyError(error);
  } finally {
    isLoading.value = false;
  }
};

// 刷新列表
const refreshList = () => {
  loadMeetings();
};

// 筛选变化
const handleFilterChange = () => {
  currentPage.value = 1;
  loadMeetings();
};

// 分页变化
const handlePageChange = () => {
  loadMeetings();
};

// 每页数量变化
const handleSizeChange = () => {
  currentPage.value = 1;
  loadMeetings();
};

// 删除会议
const handleDelete = async (meeting) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除会议"${meeting.title}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    await deleteMeeting(meeting.id);
    ElMessage.success('删除成功');
    
    // 重新加载列表
    loadMeetings();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete meeting:', error);
      ElMessage.error(getUserFriendlyError(error));
    }
  }
};

// 跳转到上传页面
const goToUpload = () => {
  router.push('/upload');
};

// 跳转到详情页
const goToDetail = (meetingId) => {
  router.push(`/meetings/${meetingId}`);
};

// 检查是否有进行中的任务需要轮询
const hasProcessingMeetings = () => {
  return meetings.value.some(m => 
    ['uploaded', 'processing', 'transcribing', 'summarizing'].includes(m.status)
  );
};

// 启动轮询
const startPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  
  pollTimer = setInterval(() => {
    if (hasProcessingMeetings()) {
      loadMeetings();
    }
  }, 5000); // 每 5 秒轮询一次
};

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

// 生命周期
onMounted(() => {
  loadMeetings();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.meeting-list-container {
  max-width: 1200px;
  margin: 40px auto;
  padding: 0 20px;
}

.list-card {
  min-height: 600px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.error-alert {
  margin-bottom: 20px;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  align-items: center;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px 0;
  color: #909399;
}

.loading-container .el-icon {
  font-size: 24px;
}

.empty-container {
  padding: 60px 0;
}

.meetings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.meeting-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.meeting-card:hover {
  transform: translateY(-2px);
}

.meeting-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  gap: 10px;
}

.meeting-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.meeting-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 14px;
}

.info-item .el-icon {
  font-size: 16px;
}

.progress-bar {
  margin-bottom: 15px;
}

.error-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background-color: #fef0f0;
  border-radius: 4px;
  margin-bottom: 15px;
}

.error-info .el-icon {
  color: #f56c6c;
  font-size: 18px;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}

.meeting-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #ebeef5;
  padding-top: 10px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
