// API响应基础接口
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 分页响应接口
export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next?: string;
  previous?: string;
}

// 文件相关类型
export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  upload_time: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  file_path?: string;
  error_message?: string;
}

// AWR解析结果类型
export interface AWRParseResult {
  id: string;
  file_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
  result_data?: {
    db_info?: DatabaseInfo;
    snapshot_info?: SnapshotInfo;
    load_profile?: LoadProfile;
    wait_events?: WaitEvent[];
    sql_stats?: SQLStatistic[];
    instance_activity?: InstanceActivity[];
  };
}

// 数据库信息
export interface DatabaseInfo {
  db_name: string;
  instance_name: string;
  version: string;
  instance_type: 'SINGLE' | 'RAC' | 'CDB' | 'PDB';
  host_name?: string;
  platform?: string;
  startup_time?: string;
  is_rac: boolean;
  container_name?: string;
  instance_number?: number;
}

// 快照信息
export interface SnapshotInfo {
  begin_snap_id: number;
  end_snap_id: number;
  begin_time: string;
  end_time: string;
  elapsed_time: number;
  db_time: number;
}

// 负载概要
export interface LoadProfile {
  logical_reads: number;
  physical_reads: number;
  physical_writes: number;
  user_calls: number;
  parses: number;
  hard_parses: number;
  sorts: number;
  logons: number;
  executes: number;
  transactions: number;
  blocks_changed: number;
  physical_read_io_requests: number;
  physical_write_io_requests: number;
  db_block_changes: number;
}

// 等待事件
export interface WaitEvent {
  event_name: string;
  waits: number;
  time_waited_ms: number;
  avg_wait_ms: number;
  percentage_db_time: number;
  wait_class?: string;
}

// SQL统计
export interface SQLStatistic {
  sql_id: string;
  executions: number;
  cpu_time: number;
  elapsed_time: number;
  logical_reads: number;
  physical_reads: number;
  rows_processed: number;
  sql_text?: string;
  module?: string;
  parsing_schema?: string;
}

// 实例活动
export interface InstanceActivity {
  statistic_name: string;
  total: number;
  per_second: number;
  per_transaction: number;
  unit?: string;
}

// 用户信息
export interface User {
  id: string;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  date_joined: string;
}

// 认证相关
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

// 错误类型
export interface ErrorInfo {
  code: string;
  message: string;
  details?: any;
}

// 统计信息
export interface Statistics {
  total_files: number;
  total_parses: number;
  success_rate: number;
  avg_parse_time: number;
  last_updated: string;
} 