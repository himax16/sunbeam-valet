# Sunbeam Valet

## Development Environment

### Opencode setup


file:  `~/.local/share/opencode/auth.json`

```
{
    "$schema": "https://opencode.ai/config.json",
    "provider": {
        "openrouter": {
            "npm": "@ai-sdk/openai-compatible",
            "name": "OpenRouter",
            "options": {
                "baseURL": "https://openrouter.ai/api/v1",
                "apiKey": "<API_KEY>"
            },
            "models": {
                "anthropic/claude-sonnet-4": {
                    "name": "Claude Sonnet 4 (OpenRouter)"
                },
                "openai/gpt-4o": {
                    "name": "GPT-4o (OpenRouter)"
                }
            }
        }
    }
}
```

### Workshop

``` sh
workshop launch
```


## References

* [OpenCode SDK for Workshop](https://github.com/canonical/opencode-sdk)
