import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface ParseResult {
  id: string;
  fileId: string;
  fileName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startTime?: string;
  endTime?: string;
  result?: {
    dbInfo?: any;
    snapshotInfo?: any;
    loadProfile?: any;
    waitEvents?: any[];
    sqlStats?: any[];
    instanceActivity?: any[];
  };
  error?: string;
}

interface ParseState {
  results: ParseResult[];
  currentParse?: ParseResult;
  loading: boolean;
}

const initialState: ParseState = {
  results: [],
  currentParse: undefined,
  loading: false,
};

// 启动解析任务
export const startParse = createAsyncThunk(
  'parse/startParse',
  async (fileId: string, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/parse/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_id: fileId }),
      });

      if (!response.ok) {
        throw new Error('Parse start failed');
      }

      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Parse failed');
    }
  }
);

// 获取解析状态
export const getParseStatus = createAsyncThunk(
  'parse/getStatus',
  async (parseId: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`/api/parse/${parseId}/status/`);
      
      if (!response.ok) {
        throw new Error('Failed to get parse status');
      }

      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Status check failed');
    }
  }
);

// 获取解析结果
export const getParseResult = createAsyncThunk(
  'parse/getResult',
  async (parseId: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`/api/parse/${parseId}/result/`);
      
      if (!response.ok) {
        throw new Error('Failed to get parse result');
      }

      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Result fetch failed');
    }
  }
);

const parseSlice = createSlice({
  name: 'parse',
  initialState,
  reducers: {
    updateParseProgress: (state, action: PayloadAction<{ id: string; progress: number }>) => {
      const parse = state.results.find(p => p.id === action.payload.id);
      if (parse) {
        parse.progress = action.payload.progress;
      }
      if (state.currentParse && state.currentParse.id === action.payload.id) {
        state.currentParse.progress = action.payload.progress;
      }
    },
    updateParseStatus: (state, action: PayloadAction<{ id: string; status: ParseResult['status']; error?: string }>) => {
      const parse = state.results.find(p => p.id === action.payload.id);
      if (parse) {
        parse.status = action.payload.status;
        if (action.payload.error) {
          parse.error = action.payload.error;
        }
        if (action.payload.status === 'completed' || action.payload.status === 'failed') {
          parse.endTime = new Date().toISOString();
        }
      }
      if (state.currentParse && state.currentParse.id === action.payload.id) {
        state.currentParse.status = action.payload.status;
        if (action.payload.error) {
          state.currentParse.error = action.payload.error;
        }
      }
    },
    setCurrentParse: (state, action: PayloadAction<ParseResult | undefined>) => {
      state.currentParse = action.payload;
    },
    clearResults: (state) => {
      state.results = [];
      state.currentParse = undefined;
    },
  },
  extraReducers: (builder) => {
    builder
      // Start parse
      .addCase(startParse.pending, (state) => {
        state.loading = true;
      })
      .addCase(startParse.fulfilled, (state, action) => {
        state.loading = false;
        const newParse: ParseResult = {
          id: action.payload.id,
          fileId: action.payload.file_id,
          fileName: action.payload.file_name,
          status: 'pending',
          progress: 0,
          startTime: new Date().toISOString(),
        };
        state.results.push(newParse);
        state.currentParse = newParse;
      })
      .addCase(startParse.rejected, (state) => {
        state.loading = false;
      })
      // Get status
      .addCase(getParseStatus.fulfilled, (state, action) => {
        const parse = state.results.find(p => p.id === action.payload.id);
        if (parse) {
          parse.status = action.payload.status;
          parse.progress = action.payload.progress;
        }
        if (state.currentParse && state.currentParse.id === action.payload.id) {
          state.currentParse.status = action.payload.status;
          state.currentParse.progress = action.payload.progress;
        }
      })
      // Get result
      .addCase(getParseResult.fulfilled, (state, action) => {
        const parse = state.results.find(p => p.id === action.payload.id);
        if (parse) {
          parse.result = action.payload.result;
          parse.status = 'completed';
        }
        if (state.currentParse && state.currentParse.id === action.payload.id) {
          state.currentParse.result = action.payload.result;
          state.currentParse.status = 'completed';
        }
      });
  },
});

export const { updateParseProgress, updateParseStatus, setCurrentParse, clearResults } = parseSlice.actions;
export default parseSlice.reducer; 