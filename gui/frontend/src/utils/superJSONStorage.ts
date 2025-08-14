import superjson from 'superjson';
import type { PersistStorage } from 'zustand/middleware';

/**
 * Storage adapter using superjson for serialization.
 * Superjson handles Maps, Sets, Dates, undefined, and other complex types
 * that standard JSON.stringify cannot properly serialize.
 * 
 * This follows the Zustand documentation pattern for custom storage.
 */
export function createSuperJSONStorage<T>(): PersistStorage<T> {
  return {
    getItem: (name) => {
      const str = localStorage.getItem(name);
      if (!str) return null;
      return superjson.parse(str);
    },
    setItem: (name, value) => {
      localStorage.setItem(name, superjson.stringify(value));
    },
    removeItem: (name) => {
      localStorage.removeItem(name);
    },
  };
}