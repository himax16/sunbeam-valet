# Sunbeam Valet

Sunbeam Valet runs a small AI-assisted triage harness for Sunbeam bug queues. It
fetches bugs from Watchtower, asks configured agents for independent triage
opinions, optionally runs a second round when confidence scores disagree, asks a
judge model to merge the result, and posts a Markdown report to Mattermost.

## Running

```sh
sunbeam-valet --config config/harness.yaml
```

The default config path is `config/harness.yaml`. Use `--log-level DEBUG` for
more verbose runtime logging.

For local validation without a running Mattermost instance, render the report to
stdout and cap the number of bugs sent to the models:

```sh
source .envrc
export WATCHTOWER_CONFIG=/path/to/sunbeam-watchtower/watchtower.yaml
sunbeam-valet --config config/harness.yaml --output stdout --limit 5
```

The harness config uses explicit pydantic-ai model IDs. For OpenRouter, prefix
models with `openrouter:`, for example:

```yaml
model: openrouter:deepseek/deepseek-v4-flash
```

Runtime configuration currently expects:

- `OPENROUTER_API_KEY` for the configured OpenRouter models
- `WATCHTOWER_CONFIG` when Watchtower should use a non-default config file
- `MATTERMOST_WEBHOOK_URL` when using the default webhook-based Mattermost
  output
- A Watchtower command that writes a JSON list of Launchpad bugs to stdout

Mattermost output supports two modes. Webhook mode posts directly to an incoming
webhook URL and does not require a bot token or channel ID:

```yaml
mattermost:
  mode: webhook
  webhook_url: "${MATTERMOST_WEBHOOK_URL}"
```

Bot mode uses Mattermost's posts API with a bot token:

```yaml
mattermost:
  mode: bot
  server_url: "${MATTERMOST_URL}"
  bot_token: "${MATTERMOST_BOT_TOKEN}"
  channel_id: "${MATTERMOST_CHANNEL_ID}"
```

Each Watchtower item may include `id` or `bug_id`, `title`, `status`,
`importance`, `description`, `url`, and `source`. The source defaults to
`launchpad`; if no description is present, the title is reused as description.

## Development Environment

### Opencode setup with OpenRouter

Write in `.envrc`
```
export OPENROUTER_API_KEY=sk-...
```

### Workshop

``` sh
workshop launch
```


## References

* [OpenCode SDK for Workshop](https://github.com/canonical/opencode-sdk)
