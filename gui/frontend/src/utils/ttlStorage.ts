// StateStorage interface compatible with Zustand persist middleware
interface StateStorage {
  getItem: (name: string) => string | null | Promise<string | null>;
  setItem: (name: string, value: string) => void | Promise<void>;
  removeItem: (name: string) => void | Promise<void>;
}

interface TTLData {
  state: unknown;
  _timestamp: number;
  _ttl: number;
}

/**
 * Creates a TTL-aware storage adapter for Zustand persist middleware.
 * Data expires after the specified TTL and is automatically cleared.
 * 
 * @param ttlHours - Time to live in hours (default: 12)
 * @returns StateStorage compatible with Zustand persist middleware
 */
export const createTTLStorage = (ttlHours: number = 12): StateStorage => ({
  getItem: (name: string): string | null => {
    try {
      const item = localStorage.getItem(name);
      if (!item) return null;
      
      const data: TTLData = JSON.parse(item);
      
      // Check if data has our TTL wrapper structure
      if (data._ttl !== undefined && data._timestamp !== undefined) {
        const age = Date.now() - data._timestamp;
        const ttlMs = ttlHours * 60 * 60 * 1000;
        
        if (age > ttlMs) {
          localStorage.removeItem(name);
          console.log(`[TTL Storage] Cleared expired data for ${name} (age: ${Math.round(age / 1000 / 60)} minutes)`);
          return null;
        }
        
        // Return the state part as a JSON string (Zustand expects string)
        return JSON.stringify(data.state);
      }
      
      // Return raw data if not TTL wrapped (backward compatibility)
      return item;
    } catch (error) {
      console.error(`[TTL Storage] Error loading ${name}:`, error);
      localStorage.removeItem(name);
      return null;
    }
  },
  
  setItem: (name: string, value: string): void => {
    try {
      // Parse the value to wrap it with TTL metadata
      const state = JSON.parse(value);
      const data: TTLData = {
        state,
        _timestamp: Date.now(),
        _ttl: ttlHours
      };
      localStorage.setItem(name, JSON.stringify(data));
    } catch (error) {
      console.error(`[TTL Storage] Error saving ${name}:`, error);
    }
  },
  
  removeItem: (name: string): void => {
    localStorage.removeItem(name);
  }
});