import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { ProviderInfo } from '../types';

interface UseProvidersReturn {
  providers: ProviderInfo[];
  loading: boolean;
  error?: string;
}

export const useProviders = (connectionStatus: 'checking' | 'connected' | 'disconnected'): UseProvidersReturn => {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    const loadProviders = async () => {
      if (connectionStatus !== 'connected') return;
      
      setLoading(true);
      setError(undefined);
      
      const response = await apiService.getProvidersInfo();
      if (response.data) {
        setProviders(response.data);
      } else {
        setError(response.error);
        setProviders([]);
      }
      setLoading(false);
    };

    loadProviders();
  }, [connectionStatus]);

  return { providers, loading, error };
};