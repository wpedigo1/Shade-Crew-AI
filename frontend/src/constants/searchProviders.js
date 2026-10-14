export const SEARCH_PROVIDERS = [
    {
        id: 'duckduckgo',
        name: 'DuckDuckGo',
        description: 'Hybrid web + news search with smart optimization. Fast and free.',
        requiresKey: false,
        keyType: null,
    },
    {
        id: 'serper',
        name: 'Serper (Google)',
        description: 'Real Google search results. 2,500 free queries. Fast and accurate.',
        requiresKey: true,
        keyType: 'serper',
    },
    {
        id: 'tavily',
        name: 'Tavily',
        description: 'Purpose-built for LLMs. Returns rich, relevant content. Requires API key.',
        requiresKey: true,
        keyType: 'tavily',
    },
    {
        id: 'brave',
        name: 'Brave Search',
        description: 'Privacy-focused search. 2,000 free queries/month. Requires API key.',
        requiresKey: true,
        keyType: 'brave',
    },
    {
        id: 'tinyfish',
        name: 'TinyFish',
        description: 'AI-powered search with free tier (5 req/min). Free API key, no credit card. Includes batch content fetching.',
        requiresKey: true,
        keyType: 'tinyfish',
    },
];
