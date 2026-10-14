import assert from 'node:assert/strict';
import { test } from 'vitest';

import { discoverConfiguredModels } from './configuredModels.js';

test('configured model discovery exposes a loader', () => {
  assert.equal(typeof discoverConfiguredModels, 'function');
});

test('loads only configured sources and preserves exact provider:model IDs', async () => {
  const calls = [];
  const client = {
    getModels: async () => {
      calls.push('openrouter');
      return { models: [{ id: 'openrouter:vendor/alpha', name: 'Alpha', provider: 'OpenRouter' }] };
    },
    getOllamaModels: async () => {
      calls.push('ollama');
      return { models: [{ id: 'should-not-load', name: 'Disabled local' }] };
    },
    getDirectModels: async () => {
      calls.push('direct');
      return [
        { id: 'openai:gpt-5', name: 'GPT-5', provider: 'OpenAI' },
        { id: 'anthropic:claude', name: 'Disabled Claude', provider: 'Anthropic' },
        { id: 'openai-oauth:gpt-5', name: 'GPT-5 Subscription', source: 'openai-oauth' },
      ];
    },
    getCustomEndpointModels: async () => {
      calls.push('custom');
      return { models: [{ id: 'custom:exact-model', name: 'Custom Exact' }] };
    },
  };
  const settings = {
    openrouter_api_key_set: true,
    openai_api_key_set: true,
    openai_oauth_connected: true,
    custom_endpoint_url: 'https://models.example.test/v1',
    ollama_base_url: 'http://localhost:11434',
    enabled_providers: {
      openrouter: true,
      ollama: false,
      direct: true,
      custom: true,
      'openai-oauth': true,
    },
    direct_provider_toggles: { openai: true, anthropic: false },
  };

  const models = await discoverConfiguredModels(client, settings);

  assert.deepEqual(calls.sort(), ['custom', 'direct', 'openrouter']);
  assert.deepEqual(models.map((model) => model.id), [
    'openrouter:vendor/alpha',
    'custom:exact-model',
    'openai:gpt-5',
    'openai-oauth:gpt-5',
  ]);
});

test('normalizes bare Ollama IDs once and isolates a failed configured source', async () => {
  const client = {
    getModels: async () => { throw new Error('catalog unavailable'); },
    getOllamaModels: async () => ({
      models: [
        { id: 'llama3', name: 'Llama 3' },
        { id: 'ollama:qwen2.5', name: 'Qwen' },
      ],
    }),
    getDirectModels: async () => [],
    getCustomEndpointModels: async () => ({ models: [] }),
  };
  const settings = {
    openrouter_api_key_set: true,
    ollama_base_url: 'http://localhost:11434',
    enabled_providers: { openrouter: true, ollama: true },
  };

  const models = await discoverConfiguredModels(client, settings);

  assert.deepEqual(models.map((model) => model.id), ['ollama:llama3', 'ollama:qwen2.5']);
  assert.equal(models.every((model) => model.provider === 'Ollama'), true);
});
