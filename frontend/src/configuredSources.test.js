import assert from 'node:assert/strict';
import { test } from 'vitest';
import { configuredSources } from './configuredModels.js';

function settings(overrides = {}) {
  return { enabled_providers: {}, ...overrides };
}

test('reports every source connected when all credentials are configured', () => {
  const sources = configuredSources(settings({
    openrouter_api_key_set: true,
    ollama_base_url: 'http://localhost:11434',
    openai_api_key_set: true,
    custom_endpoint_url: 'http://localhost:8765',
    xai_oauth_connected: true,
    openai_oauth_connected: true,
    github_copilot_connected: true,
  }));
  assert.deepEqual(sources, {
    openrouter: true,
    ollama: true,
    direct: true,
    custom: true,
    oauth: true,
  });
});

test('reports no sources when nothing is configured', () => {
  assert.deepEqual(configuredSources(settings({})), {
    openrouter: false,
    ollama: false,
    direct: false,
    custom: false,
    oauth: false,
  });
});

test('a provider explicitly disabled in enabled_providers stays off despite credentials', () => {
  const sources = configuredSources(settings({
    openrouter_api_key_set: true,
    openai_api_key_set: true,
    xai_oauth_connected: true,
    enabled_providers: { openrouter: false, direct: false, 'xai-oauth': false },
  }));
  assert.deepEqual(sources, {
    openrouter: false,
    ollama: false,
    direct: false,
    custom: false,
    oauth: false,
  });
});

test('oauth requires both a connected flag and the provider not being disabled', () => {
  assert.equal(configuredSources(settings({ openai_oauth_connected: true })).oauth, true);
  assert.equal(
    configuredSources(settings({ openai_oauth_connected: true, enabled_providers: { 'openai-oauth': false } })).oauth,
    false,
  );
});

test('direct requires at least one configured direct key flag', () => {
  assert.equal(configuredSources(settings({ deepseek_api_key_set: true })).direct, true);
  assert.equal(configuredSources(settings({})).direct, false);
});