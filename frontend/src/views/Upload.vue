<template>
  <div class="upload-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>上传会议音频</span>
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
      
      <!-- 成功提示 -->
      <el-alert
        v-if="successMessage"
        :title="successMessage"
        type="success"
        :closable="true"
        @close="successMessage = ''"
        class="success-alert"
      />
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="upload-form"
      >
        <!-- 会议标题 -->
        <el-form-item label="会议标题" prop="title">
          <el-input
            v-model="form.title"
            placeholder="请输入会议标题"
            maxlength="200"
            show-word-limit
            :disabled="isUploading"
          />
        </el-form-item>
        
        <!-- 会议日期 -->
        <el-form-item label="会议日期" prop="date">
          <el-date-picker
            v-model="form.date"
            type="date"
            placeholder="请选择会议日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled="isUploading"
          />
        </el-form-item>
        
        <!-- 参会人员 -->
        <el-form-item label="参会人员" prop="participants">
          <el-input
            v-model="form.participants"
            type="textarea"
            :rows="3"
            placeholder="请输入参会人员（多个用逗号分隔）"
            :disabled="isUploading"
          />
        </el-form-item>
        
        <!-- 音频文件上传 -->
        <el-form-item label="音频文件" prop="audio">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :show-file-list="true"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :before-upload="beforeUpload"
            :file-list="fileList"
            accept=".mp3,.wav,.m4a,.ogg,.flac"
            :disabled="isUploading"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持格式：MP3, WAV, M4A, OGG, FLAC，最大 500MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <!-- 上传进度 -->
        <el-form-item v-if="isUploading" label="上传进度">
          <el-progress :percentage="uploadProgress" :status="uploadProgress === 100 ? 'success' : undefined" />
        </el-form-item>
        
        <!-- 按钮区域 -->
        <el-form-item>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="isUploading"
            :disabled="!canSubmit"
          >
            {{ isUploading ? '处理中...' : '开始处理' }}
          </el-button>
          <el-button @click="handleReset" :disabled="isUploading">
            重置
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 处理进度提示 -->
      <div v-if="isUploading" class="processing-info">
        <el-icon class="is-loading"><loading /></el-icon>
        <span>{{ processingStatusText }}</span>
      </div>
    </el-card>
    
    <!-- 上传成功后的跳转提示 -->
    <div v-if="uploadedMeetingId" class="success-navigation">
      <el-card>
        <div class="navigation-content">
          <el-icon class="success-icon"><success-filled /></el-icon>
          <div class="text-content">
            <h3>上传成功！</h3>
            <p>会议录音正在后台处理中，您可以查看处理进度或返回列表。</p>
          </div>
          <div class="button-group">
            <el-button type="primary" @click="goToDetail">
              查看详情
            </el-button>
            <el-button @click="goToList">
              返回列表
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  UploadFilled,
  Loading,
  SuccessFilled
} from '@element-plus/icons-vue';
import {
  uploadMeeting,
  getUserFriendlyError,
  ApiError
} from '../api';

const router = useRouter();

// 表单引用
const formRef = ref(null);
const uploadRef = ref(null);

// 状态
const isUploading = ref(false);
const uploadProgress = ref(0);
const errorMessage = ref('');
const successMessage = ref('');
const uploadedMeetingId = ref('');
const processingStatusText = ref('正在上传文件...');

// 表单数据
const form = reactive({
  title: '',
  date: '',
  participants: '',
  audio: null
});

// 文件列表
const fileList = ref([]);

// 表单验证规则
const rules = {
  title: [
    { required: true, message: '请输入会议标题', trigger: 'blur' },
    { min: 1, max: 200, message: '会议标题长度在 1 到 200 个字符', trigger: 'blur' }
  ],
  audio: [
    { required: true, message: '请选择音频文件', trigger: 'change' }
  ]
};

// 计算属性
const canSubmit = computed(() => {
  return form.title && fileList.value.length > 0 && !isUploading.value;
});

// 文件改变
const handleFileChange = (file) => {
  form.audio = file.raw;
  
  // 验证文件类型
  const allowedExtensions = ['mp3', 'wav', 'm4a', 'ogg', 'flac'];
  const fileName = file.name.toLowerCase();
  const fileExt = fileName.split('.').pop();
  
  if (!allowedExtensions.includes(fileExt)) {
    errorMessage.value = `不支持的文件格式。支持的格式: ${allowedExtensions.join(', ')}`;
    handleFileRemove();
    return;
  }
  
  // 验证文件大小 (500MB)
  const maxSize = 500 * 1024 * 1024;
  if (file.size > maxSize) {
    errorMessage.value = '文件大小超过限制，最大允许 500MB';
    handleFileRemove();
    return;
  }
  
  errorMessage.value = '';
};

// 文件移除
const handleFileRemove = () => {
  form.audio = null;
  fileList.value = [];
};

// 上传前检查
const beforeUpload = (file) => {
  const allowedExtensions = ['mp3', 'wav', 'm4a', 'ogg', 'flac'];
  const fileName = file.name.toLowerCase();
  const fileExt = fileName.split('.').pop();
  
  if (!allowedExtensions.includes(fileExt)) {
    ElMessage.error(`不支持的文件格式: ${fileExt}`);
    return false;
  }
  
  const maxSize = 500 * 1024 * 1024;
  if (file.size > maxSize) {
    ElMessage.error('文件大小超过限制，最大允许 500MB');
    return false;
  }
  
  return true;
};

// 显示错误
const showError = (error) => {
  const userMessage = getUserFriendlyError(error);
  errorMessage.value = userMessage;
  
  console.error('Upload error:', error);
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;
  
  // 验证表单
  try {
    await formRef.value.validate();
  } catch (e) {
    errorMessage.value = '请填写必要的信息';
    return;
  }
  
  if (!form.audio) {
    errorMessage.value = '请选择音频文件';
    return;
  }
  
  // 清除之前的消息
  errorMessage.value = '';
  successMessage.value = '';
  
  // 开始上传
  isUploading.value = true;
  uploadProgress.value = 0;
  processingStatusText.value = '正在上传文件...';
  uploadedMeetingId.value = '';
  
  try {
    const result = await uploadMeeting(
      form.audio,
      form.title,
      form.date,
      form.participants,
      (progress) => {
        uploadProgress.value = progress;
        if (progress < 100) {
          processingStatusText.value = `正在上传文件... ${progress}%`;
        } else {
          processingStatusText.value = '文件上传完成，正在启动处理...';
        }
      }
    );
    
    uploadProgress.value = 100;
    processingStatusText.value = '处理任务已启动！';
    successMessage.value = '上传成功！会议录音正在后台处理中。';
    
    // 保存会议ID以便后续跳转
    if (result.data && result.data.meeting_id) {
      uploadedMeetingId.value = result.data.meeting_id;
    }
    
    ElMessage.success('上传成功！');
    
  } catch (error) {
    console.error('Upload failed:', error);
    showError(error);
  } finally {
    isUploading.value = false;
  }
};

// 重置表单
const handleReset = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  form.date = '';
  form.participants = '';
  handleFileRemove();
  errorMessage.value = '';
  successMessage.value = '';
  uploadedMeetingId.value = '';
  uploadProgress.value = 0;
};

// 跳转到详情页
const goToDetail = () => {
  if (uploadedMeetingId.value) {
    router.push(`/meetings/${uploadedMeetingId.value}`);
  }
};

// 跳转到列表页
const goToList = () => {
  router.push('/meetings');
};
</script>

<style scoped>
.upload-container {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 20px;
}

.upload-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.error-alert,
.success-alert {
  margin-bottom: 20px;
}

.upload-form {
  margin-top: 20px;
}

.processing-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px;
  background-color: #f0f9ff;
  border-radius: 4px;
  margin-top: 20px;
  color: #0066cc;
}

.processing-info .el-icon {
  font-size: 20px;
}

.success-navigation {
  margin-top: 20px;
}

.navigation-content {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
}

.success-icon {
  font-size: 48px;
  color: #67c23a;
}

.text-content {
  flex: 1;
}

.text-content h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: #303133;
}

.text-content p {
  margin: 0;
  color: #606266;
}

.button-group {
  display: flex;
  gap: 10px;
}

:deep(.el-upload-dragger) {
  width: 100%;
}
</style>
