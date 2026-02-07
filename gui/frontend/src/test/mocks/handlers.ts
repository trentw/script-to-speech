import { http, HttpResponse } from 'msw';

import { BACKEND_URL } from '@/config';
import {
  TEST_PROVIDERS,
  TEST_TASK_PENDING,
  TEST_VOICES,
} from '@/test/utils/test-data';

const API_BASE_URL = BACKEND_URL;

export const handlers = [
  // Success handlers
  http.get(`${API_BASE_URL}/api/providers/info`, () => {
    return HttpResponse.json(TEST_PROVIDERS);
  }),

  http.get(`${API_BASE_URL}/api/backend/status`, () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '2.0.0',
      uptime: 3600,
    });
  }),

  // Health check endpoint
  http.get(`${API_BASE_URL}/health`, () => {
    return new HttpResponse(null, { status: 200 });
  }),

  http.get(`${API_BASE_URL}/api/voice-library/voices`, () => {
    return HttpResponse.json({
      voices: TEST_VOICES,
    });
  }),

  http.get(`${API_BASE_URL}/api/tasks`, () => {
    return HttpResponse.json({
      tasks: [TEST_TASK_PENDING],
    });
  }),

  http.get(`${API_BASE_URL}/api/tasks/:taskId`, ({ params }) => {
    const { taskId } = params;
    return HttpResponse.json({
      task_id: taskId as string,
      status: 'completed',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message: 'Task completed successfully',
      result: {
        audio_url: `/api/audio/${taskId}.mp3`,
        duration: 10.5,
      },
    });
  }),

  http.post(
    `${API_BASE_URL}/api/generate/standalone-speech`,
    async ({ request }) => {
      await request.json(); // Read body but don't store in unused variable
      return HttpResponse.json({
        task_id: 'new-task-123',
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message: 'Task created successfully',
      });
    }
  ),

  // Error scenario handlers
  http.get(
    `${API_BASE_URL}/api/providers/info`,
    () => {
      return new HttpResponse(null, { status: 500 });
    },
    { once: true }
  ),

  http.get(
    `${API_BASE_URL}/api/backend/status`,
    () => {
      return new HttpResponse(null, { status: 503 });
    },
    { once: true }
  ),

  http.post(
    `${API_BASE_URL}/api/generate/standalone-speech`,
    () => {
      return HttpResponse.json(
        {
          detail: 'Invalid request: missing required field "text"',
        },
        { status: 400 }
      );
    },
    { once: true }
  ),

  http.get(
    `${API_BASE_URL}/api/tasks/:taskId`,
    () => {
      return HttpResponse.json(
        {
          detail: 'Task not found',
        },
        { status: 404 }
      );
    },
    { once: true }
  ),
];
