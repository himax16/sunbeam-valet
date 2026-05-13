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

Runtime configuration currently expects:

- `MATTERMOST_URL`
- `MATTERMOST_BOT_TOKEN`
- `MATTERMOST_CHANNEL_ID`
- A Watchtower command that writes a JSON list of Launchpad bugs to stdout

Each Watchtower item may include `id`, `title`, `status`, `importance`,
`description`, `url`, and `source`. The source defaults to `launchpad`.

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
