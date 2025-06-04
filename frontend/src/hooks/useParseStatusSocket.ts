import { useState, useEffect, useRef, useCallback } from 'react';
import { message } from 'antd';
import { ParseStatus } from '../components/ParseProgress';

interface WebSocketMessage {
  type: 'status_update' | 'error' | 'complete' | 'cancelled';
  data: any;
  parseId?: string;
}

interface UseParseStatusSocketOptions {
  parseId: string;
  onStatusUpdate?: (status: ParseStatus) => void;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
  onCancel?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface SocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
}

export const useParseStatusSocket = ({
  parseId,
  onStatusUpdate,
  onComplete,
  onError,
  onCancel,
  autoReconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5
}: UseParseStatusSocketOptions) => {
  const [socketState, setSocketState] = useState<SocketState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const shouldConnect = useRef(true);

  // 清理定时器
  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  // 连接WebSocket - 高内聚低耦合
  const connect = useCallback(() => {
    if (!shouldConnect.current || ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setSocketState(prev => ({ ...prev, connecting: true, error: null }));

    try {
      // 构建WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/parse-status/${parseId}/`;
      
      ws.current = new WebSocket(wsUrl);

      // 连接成功
      ws.current.onopen = () => {
        console.log('WebSocket连接已建立');
        setSocketState(prev => ({
          ...prev,
          connected: true,
          connecting: false,
          error: null,
          reconnectAttempts: 0
        }));
        clearReconnectTimer();
      };

      // 接收消息 - 单一职责原则
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // 验证消息是否属于当前解析任务
          if (message.parseId && message.parseId !== parseId) {
            return;
          }

          switch (message.type) {
            case 'status_update':
              if (onStatusUpdate && message.data) {
                onStatusUpdate(message.data as ParseStatus);
              }
              break;
              
            case 'complete':
              if (onComplete) {
                onComplete(message.data);
              }
              // 完成后断开连接
              shouldConnect.current = false;
              ws.current?.close();
              break;
              
            case 'error':
              if (onError) {
                onError(message.data?.error || '解析过程中发生错误');
              }
              break;
              
            case 'cancelled':
              if (onCancel) {
                onCancel();
              }
              // 取消后断开连接
              shouldConnect.current = false;
              ws.current?.close();
              break;
              
            default:
              console.warn('未知的WebSocket消息类型:', message.type);
          }
        } catch (err) {
          console.error('解析WebSocket消息失败:', err);
        }
      };

      // 连接错误
      ws.current.onerror = (error) => {
        console.error('WebSocket连接错误:', error);
        setSocketState(prev => ({
          ...prev,
          connected: false,
          connecting: false,
          error: 'WebSocket连接错误'
        }));
      };

      // 连接关闭
      ws.current.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason);
        setSocketState(prev => ({
          ...prev,
          connected: false,
          connecting: false
        }));

        // 自动重连逻辑
        if (shouldConnect.current && autoReconnect) {
          const { reconnectAttempts } = socketState;
          
          if (reconnectAttempts < maxReconnectAttempts) {
            console.log(`WebSocket重连中... (${reconnectAttempts + 1}/${maxReconnectAttempts})`);
            
            setSocketState(prev => ({
              ...prev,
              reconnectAttempts: prev.reconnectAttempts + 1
            }));

            reconnectTimer.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else {
            console.error('WebSocket重连次数已达上限');
            setSocketState(prev => ({
              ...prev,
              error: '连接失败，已达最大重连次数'
            }));
            message.error('实时连接断开，请刷新页面重试');
          }
        }
      };

    } catch (err) {
      console.error('创建WebSocket连接失败:', err);
      setSocketState(prev => ({
        ...prev,
        connecting: false,
        error: '创建WebSocket连接失败'
      }));
    }
  }, [parseId, onStatusUpdate, onComplete, onError, onCancel, autoReconnect, reconnectInterval, maxReconnectAttempts, socketState.reconnectAttempts]);

  // 断开连接
  const disconnect = useCallback(() => {
    shouldConnect.current = false;
    clearReconnectTimer();
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setSocketState({
      connected: false,
      connecting: false,
      error: null,
      reconnectAttempts: 0
    });
  }, [clearReconnectTimer]);

  // 手动重连
  const reconnect = useCallback(() => {
    disconnect();
    shouldConnect.current = true;
    setSocketState(prev => ({ ...prev, reconnectAttempts: 0 }));
    connect();
  }, [disconnect, connect]);

  // 发送消息（如果需要）
  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // 组件挂载时建立连接
  useEffect(() => {
    if (parseId) {
      shouldConnect.current = true;
      connect();
    }

    // 组件卸载时清理
    return () => {
      shouldConnect.current = false;
      clearReconnectTimer();
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [parseId, connect, clearReconnectTimer]);

  // 页面可见性变化处理
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 页面隐藏时暂停重连
        shouldConnect.current = false;
        clearReconnectTimer();
      } else {
        // 页面显示时恢复连接
        if (!socketState.connected && parseId) {
          shouldConnect.current = true;
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [socketState.connected, parseId, connect, clearReconnectTimer]);

  return {
    ...socketState,
    connect,
    disconnect,
    reconnect,
    sendMessage
  };
}; 