import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface UploadFile {
  id: string;
  name: string;
  size: number;
  status: 'uploading' | 'done' | 'error' | 'removed';
  progress: number;
  response?: any;
  error?: string;
}

interface UploadState {
  files: UploadFile[];
  uploading: boolean;
  uploadProgress: number;
}

const initialState: UploadState = {
  files: [],
  uploading: false,
  uploadProgress: 0,
};

// 异步上传thunk
export const uploadFile = createAsyncThunk(
  'upload/uploadFile',
  async (file: File, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload/', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Upload failed');
    }
  }
);

const uploadSlice = createSlice({
  name: 'upload',
  initialState,
  reducers: {
    addFile: (state, action: PayloadAction<Omit<UploadFile, 'id'>>) => {
      const newFile: UploadFile = {
        ...action.payload,
        id: Date.now().toString(),
      };
      state.files.push(newFile);
    },
    updateFileProgress: (state, action: PayloadAction<{ id: string; progress: number }>) => {
      const file = state.files.find(f => f.id === action.payload.id);
      if (file) {
        file.progress = action.payload.progress;
      }
    },
    updateFileStatus: (state, action: PayloadAction<{ id: string; status: UploadFile['status']; error?: string }>) => {
      const file = state.files.find(f => f.id === action.payload.id);
      if (file) {
        file.status = action.payload.status;
        if (action.payload.error) {
          file.error = action.payload.error;
        }
      }
    },
    removeFile: (state, action: PayloadAction<string>) => {
      state.files = state.files.filter(f => f.id !== action.payload);
    },
    clearFiles: (state) => {
      state.files = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(uploadFile.pending, (state) => {
        state.uploading = true;
        state.uploadProgress = 0;
      })
      .addCase(uploadFile.fulfilled, (state, action) => {
        state.uploading = false;
        state.uploadProgress = 100;
      })
      .addCase(uploadFile.rejected, (state, action) => {
        state.uploading = false;
        state.uploadProgress = 0;
      });
  },
});

export const { addFile, updateFileProgress, updateFileStatus, removeFile, clearFiles } = uploadSlice.actions;
export default uploadSlice.reducer; 