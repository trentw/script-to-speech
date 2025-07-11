import { useState, useEffect } from 'react';
import { apiService } from '../services/api';

interface UseBackendStatusReturn {
  connectionStatus: 'checking' | 'connected' | 'disconnected';
  checkBackendStatus: () => Promise<void>;
}

export const useBackendStatus = (): UseBackendStatusReturn => {
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  const checkBackendStatus = async () => {
    try {
      const isHealthy = await apiService.healthCheck();
      setConnectionStatus(isHealthy ? 'connected' : 'disconnected');
    } catch {
      setConnectionStatus('disconnected');
    }
  };

  useEffect(() => {
    // Check initial status
    checkBackendStatus();
    
    // Set up periodic checking every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return { connectionStatus, checkBackendStatus };
};