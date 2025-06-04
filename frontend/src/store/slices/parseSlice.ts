import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ParseStatus, ParseStage } from '../../components/ParseProgress';

// 解析任务状态接口
export interface ParseTask {
  id: string;
  fileId: string;
  fileName: string;
  status: ParseStatus['status'];
  progress: number;
  currentStep: string;
  startTime?: string;
  endTime?: string;
  estimatedTimeRemaining?: number;
  error?: string;
  stages: ParseStage[];
  resultId?: string;
}

// Redux状态接口
interface ParseState {
  tasks: { [key: string]: ParseTask };
  activeTasks: string[];
  recentTasks: string[];
  isConnecting: boolean;
  connectionError: string | null;
}

// 初始状态
const initialState: ParseState = {
  tasks: {},
  activeTasks: [],
  recentTasks: [],
  isConnecting: false,
  connectionError: null
};

// 异步action：开始解析 - SOLID原则：单一职责
export const startParsing = createAsyncThunk(
  'parse/startParsing',
  async (params: { fileId: string; fileName: string }) => {
    const response = await fetch('/api/start-parsing/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ file_id: params.fileId })
    });

    if (!response.ok) {
      throw new Error('启动解析失败');
    }

    const data = await response.json();
    return {
      taskId: data.task_id,
      fileId: params.fileId,
      fileName: params.fileName
    };
  }
);

// 异步action：取消解析
export const cancelParsing = createAsyncThunk(
  'parse/cancelParsing',
  async (taskId: string) => {
    const response = await fetch(`/api/parse-cancel/${taskId}/`, {
      method: 'POST'
    });

    if (!response.ok) {
      throw new Error('取消解析失败');
    }

    return { taskId };
  }
);

// 异步action：获取解析历史
export const fetchParseHistory = createAsyncThunk(
  'parse/fetchHistory',
  async () => {
    const response = await fetch('/api/parse-history/');
    
    if (!response.ok) {
      throw new Error('获取解析历史失败');
    }

    const data = await response.json();
    return data.results || [];
  }
);

// 解析slice
const parseSlice = createSlice({
  name: 'parse',
  initialState,
  reducers: {
    // 实时状态更新 - WebSocket消息处理
    updateTaskStatus: (state, action: PayloadAction<{ taskId: string; status: ParseStatus }>) => {
      const { taskId, status } = action.payload;
      
      if (state.tasks[taskId]) {
        state.tasks[taskId] = {
          ...state.tasks[taskId],
          status: status.status,
          progress: status.progress,
          currentStep: status.currentStep,
          estimatedTimeRemaining: status.estimatedTimeRemaining,
          error: status.error,
          stages: status.stages,
          endTime: status.endTime
        };
      }
    },

    // 添加新解析任务
    addParseTask: (state, action: PayloadAction<ParseTask>) => {
      const task = action.payload;
      state.tasks[task.id] = task;
      
      // 添加到活跃任务列表
      if (!state.activeTasks.includes(task.id)) {
        state.activeTasks.push(task.id);
      }
    },

    // 完成解析任务
    completeParseTask: (state, action: PayloadAction<{ taskId: string; resultId?: string }>) => {
      const { taskId, resultId } = action.payload;
      
      if (state.tasks[taskId]) {
        state.tasks[taskId].status = 'completed';
        state.tasks[taskId].progress = 100;
        state.tasks[taskId].endTime = new Date().toISOString();
        
        if (resultId) {
          state.tasks[taskId].resultId = resultId;
        }
        
        // 从活跃任务移除，添加到最近任务
        state.activeTasks = state.activeTasks.filter(id => id !== taskId);
        
        if (!state.recentTasks.includes(taskId)) {
          state.recentTasks.unshift(taskId);
          // 保持最近任务列表不超过10个
          if (state.recentTasks.length > 10) {
            state.recentTasks = state.recentTasks.slice(0, 10);
          }
        }
      }
    },

    // 任务失败
    failParseTask: (state, action: PayloadAction<{ taskId: string; error: string }>) => {
      const { taskId, error } = action.payload;
      
      if (state.tasks[taskId]) {
        state.tasks[taskId].status = 'failed';
        state.tasks[taskId].error = error;
        state.tasks[taskId].endTime = new Date().toISOString();
        
        // 从活跃任务移除
        state.activeTasks = state.activeTasks.filter(id => id !== taskId);
      }
    },

    // 取消解析任务
    cancelParseTask: (state, action: PayloadAction<{ taskId: string }>) => {
      const { taskId } = action.payload;
      
      if (state.tasks[taskId]) {
        state.tasks[taskId].status = 'cancelled';
        state.tasks[taskId].endTime = new Date().toISOString();
        
        // 从活跃任务移除
        state.activeTasks = state.activeTasks.filter(id => id !== taskId);
      }
    },

    // WebSocket连接状态管理
    setConnectionState: (state, action: PayloadAction<{ connecting: boolean; error?: string }>) => {
      const { connecting, error } = action.payload;
      state.isConnecting = connecting;
      state.connectionError = error || null;
    },

    // 清理已完成的任务 - 内存管理
    clearCompletedTasks: (state) => {
      const completedTaskIds = Object.keys(state.tasks).filter(
        id => ['completed', 'failed', 'cancelled'].includes(state.tasks[id].status)
      );
      
      completedTaskIds.forEach(id => {
        delete state.tasks[id];
      });
      
      state.recentTasks = state.recentTasks.filter(id => state.tasks[id]);
    },

    // 重置解析状态
    resetParseState: (state) => {
      return initialState;
    }
  },
  
  extraReducers: (builder) => {
    builder
      // 开始解析
      .addCase(startParsing.pending, (state) => {
        state.connectionError = null;
      })
      .addCase(startParsing.fulfilled, (state, action) => {
        const { taskId, fileId, fileName } = action.payload;
        
        const newTask: ParseTask = {
          id: taskId,
          fileId,
          fileName,
          status: 'pending',
          progress: 0,
          currentStep: '准备开始解析...',
          startTime: new Date().toISOString(),
          stages: [
            { name: '文件验证', status: 'pending', progress: 0 },
            { name: '解析数据库信息', status: 'pending', progress: 0 },
            { name: '解析Load Profile', status: 'pending', progress: 0 },
            { name: '解析Wait Events', status: 'pending', progress: 0 },
            { name: '解析SQL Statistics', status: 'pending', progress: 0 }
          ]
        };
        
        state.tasks[taskId] = newTask;
        
        if (!state.activeTasks.includes(taskId)) {
          state.activeTasks.push(taskId);
        }
      })
      .addCase(startParsing.rejected, (state, action) => {
        state.connectionError = action.error.message || '启动解析失败';
      })
      
      // 取消解析
      .addCase(cancelParsing.fulfilled, (state, action) => {
        const { taskId } = action.payload;
        
        if (state.tasks[taskId]) {
          state.tasks[taskId].status = 'cancelled';
          state.tasks[taskId].endTime = new Date().toISOString();
          state.activeTasks = state.activeTasks.filter(id => id !== taskId);
        }
      })
      
      // 获取历史记录
      .addCase(fetchParseHistory.fulfilled, (state, action) => {
        const historyTasks = action.payload;
        
        historyTasks.forEach((task: any) => {
          if (!state.tasks[task.id]) {
            state.tasks[task.id] = {
              id: task.id,
              fileId: task.file_id,
              fileName: task.file_name || 'unknown',
              status: task.status,
              progress: task.progress,
              currentStep: task.current_step || '',
              startTime: task.start_time,
              endTime: task.end_time,
              error: task.error,
              stages: task.stages || [],
              resultId: task.result_id
            };
            
            if (['completed', 'failed', 'cancelled'].includes(task.status)) {
              if (!state.recentTasks.includes(task.id)) {
                state.recentTasks.push(task.id);
              }
            } else if (task.status === 'running') {
              if (!state.activeTasks.includes(task.id)) {
                state.activeTasks.push(task.id);
              }
            }
          }
        });
        
        // 保持最近任务列表有序
        state.recentTasks.sort((a, b) => {
          const taskA = state.tasks[a];
          const taskB = state.tasks[b];
          const timeA = taskA.endTime || taskA.startTime || '';
          const timeB = taskB.endTime || taskB.startTime || '';
          return timeB.localeCompare(timeA);
        });
      });
  }
});

// 导出actions
export const {
  updateTaskStatus,
  addParseTask,
  completeParseTask,
  failParseTask,
  cancelParseTask,
  setConnectionState,
  clearCompletedTasks,
  resetParseState
} = parseSlice.actions;

// 选择器 - 高内聚
export const selectActiveTasks = (state: { parse: ParseState }) => 
  state.parse.activeTasks.map(id => state.parse.tasks[id]).filter(Boolean);

export const selectRecentTasks = (state: { parse: ParseState }) =>
  state.parse.recentTasks.map(id => state.parse.tasks[id]).filter(Boolean);

export const selectTaskById = (state: { parse: ParseState }, taskId: string) =>
  state.parse.tasks[taskId];

export const selectConnectionState = (state: { parse: ParseState }) => ({
  isConnecting: state.parse.isConnecting,
  connectionError: state.parse.connectionError
});

export default parseSlice.reducer; 