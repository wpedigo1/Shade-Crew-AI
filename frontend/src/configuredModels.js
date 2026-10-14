import { filterOAuthModels, OAUTH_PROVIDERS } from './constants/oauthProviders.js';

const DIRECT_PROVIDER_KEY_FLAGS = {
  openai: 'openai_api_key_set',
  anthropic: 'anthropic_api_key_set',
  google: 'google_api_key_set',
  mistral: 'mistral_api_key_set',
  deepseek: 'deepseek_api_key_set',
  groq: 'groq_api_key_set',
  nvidia: 'nvidia_api_key_set',
  'opencode-zen': 'opencode_api_key_set',
  'opencode-go': 'opencode_api_key_set',
};

function providerKey(model) {
  return (model.provider || '').toLowerCase().trim().replace(/\s+/g, '-');
}

export function configuredSources(settings) {
  const enabled = settings.enabled_providers || {};
  const hasDirect = Object.values(DIRECT_PROVIDER_KEY_FLAGS)
    .some((flag) => settings[flag]);
  const hasOAuth = OAUTH_PROVIDERS.some(
    (provider) => settings[provider.connectedKey] && enabled[provider.id] !== false,
  );
  return {
    openrouter: !!settings.openrouter_api_key_set && enabled.openrouter !== false,
    ollama: !!settings.ollama_base_url && enabled.ollama !== false,
    direct: hasDirect && enabled.direct !== false,
    custom: !!settings.custom_endpoint_url && enabled.custom !== false,
    oauth: hasOAuth,
  };
}

function filterDirectModels(models, settings) {
  const enabled = settings.enabled_providers || {};
  const toggles = settings.direct_provider_toggles || {};
  return models.filter((model) => {
    if (model.id?.startsWith('xai-oauth:')
      || model.id?.startsWith('openai-oauth:')
      || model.id?.startsWith('github-copilot:')) return false;
    const key = providerKey(model);
    if (key === 'groq' && enabled.groq === false) return false;
    if (toggles[key] === false) return false;
    const flag = DIRECT_PROVIDER_KEY_FLAGS[key];
    return flag ? !!settings[flag] : false;
  });
}

const safe = async (request, fallback) => {
  try {
    return await request();
  } catch {
    return fallback;
  }
};

export async function discoverConfiguredModels(client, settings) {
  const sources = configuredSources(settings);
  const directPromise = sources.direct || sources.oauth
    ? safe(() => client.getDirectModels(), [])
    : Promise.resolve([]);
  const [openrouter, ollama, direct, custom] = await Promise.all([
    sources.openrouter ? safe(() => client.getModels(), { models: [] }) : { models: [] },
    sources.ollama
      ? safe(() => client.getOllamaModels(settings.ollama_base_url), { models: [] })
      : { models: [] },
    directPromise,
    sources.custom ? safe(() => client.getCustomEndpointModels(), { models: [] }) : { models: [] },
  ]);
  const directModels = Array.isArray(direct) ? direct : (direct.models || []);
  const ollamaModels = (ollama.models || []).map((model) => ({
    ...model,
    id: model.id.startsWith('ollama:') ? model.id : `ollama:${model.id}`,
    name: `${model.name || model.id} (Local)`,
    provider: 'Ollama',
  }));
  const combined = [
    ...(openrouter.models || []),
    ...ollamaModels,
    ...(sources.direct ? filterDirectModels(directModels, settings) : []),
    ...(custom.models || []),
    ...(sources.oauth ? filterOAuthModels(directModels, settings) : []),
  ];
  const unique = new Map();
  combined.forEach((model) => unique.set(model.id, model));
  return Array.from(unique.values())
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''));
}
