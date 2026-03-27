import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage } from '../types/api';

const WS_URL = 'ws://localhost:8766/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT = 10;

export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retriesRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage;
          onMessage(msg);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (retriesRef.current < MAX_RECONNECT) {
          retriesRef.current += 1;
          setTimeout(connect, RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setConnected(false);
    }
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, send };
}
