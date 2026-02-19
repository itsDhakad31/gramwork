# gramwork

Telegram user-agent framework for autonomous AI agents. Gives an LLM direct control over a real Telegram account through tool-use.

Built on Telethon (MTProto), with built-in Ollama and OpenAI-compatible LLM providers, an AES-256 encrypted vault for secrets, and a ReAct engine that lets the model decide what to do on its own.

## Why not just use a bot?

Telegram bots sit behind the Bot API. They can only respond when spoken to, can't join groups on their own, can't message people first, and everyone sees the `[BOT]` badge. gramwork controls a regular user account — it can do anything a human can, and nobody can tell the difference.

## Features

- Autonomous ReAct loop — the LLM picks which tools to call, reads results, and decides next steps
- 13 Telegram tools (send, reply, forward, delete, read history, search, list chats, join/leave groups, etc.)
- Ollama provider with custom `base_url` for remote instances
- OpenAI-compatible provider (works with Groq, Together, vLLM, LM Studio, anything that speaks `/v1/chat/completions`)
- AES-256-GCM vault — all secrets encrypted on disk, derived from a master password with PBKDF2 (600k iterations)
- Encrypted session storage for Telethon
- Tool whitelist so you can restrict what the LLM is allowed to do
- Token-bucket rate limiting on outbound actions
- JSONL audit log for every tool call (name, args, result, duration)
- FastAPI-style handler mode if you don't need autonomy (`@app.on_message()`)
- Plugin system with entry-point discovery
- Starlette-style middleware pipeline
- CLI for everything (`gramwork run`, `gramwork vault`, `gramwork new`)

## Getting started

### Get your Telegram API credentials

Go to https://my.telegram.org/apps, log in with the phone number you want the agent to use, and create an app. You'll get an **API ID** and **API Hash**.

### Install

```bash
git clone https://github.com/poptye/gramwork.git
cd gramwork
pip install -e ".[dev]"
```

### Set up the vault

```bash
gramwork vault init
gramwork vault set telegram_api_id "YOUR_API_ID"
gramwork vault set telegram_api_hash "YOUR_API_HASH"
gramwork vault set telegram_phone "+1234567890"
```

The master password is never stored. Secrets are encrypted with AES-256-GCM and can only be decrypted by providing the password again.

### Write a config

```toml
[telegram]
api_id = "vault:telegram_api_id"
api_hash = "vault:telegram_api_hash"
phone = "vault:telegram_phone"
session_name = "my_agent"

[llm]
provider = "ollama"
model = "llama3.1"
base_url = "http://localhost:11434"

[agent]
autonomous = true
system_prompt = "You are an autonomous Telegram agent. Respond helpfully to incoming messages."
tools = ["send_message", "reply_message", "get_messages", "get_dialogs", "get_me"]
max_iterations = 10
loop_interval = 0.0

[safety]
rate_limit_per_chat = 3.0
rate_limit_global = 20.0
```

The `vault:` prefix tells gramwork to pull that value from the encrypted vault at runtime.

### Run it

```bash
gramwork run -c config.toml
```

First time around Telethon will ask for a confirmation code. After that the session is cached.

You can skip the password prompt by setting `GRAMWORK_MASTER_PASSWORD` as an env var.

## Config reference

**[telegram]** — `api_id` (int), `api_hash` (str), `phone` (str), `session_name` (str, default `"gramwork"`). All support `vault:` references.

**[llm]** — `provider` (`"ollama"` or `"openai_compat"`), `model`, `base_url`, `api_key` (supports `vault:`), `temperature` (0.7), `max_tokens` (4096), `timeout` (120s).

**[agent]** — `autonomous` (bool), `system_prompt` or `system_prompt_file`, `tools` (list or null for all), `max_iterations` (20), `loop_interval` (seconds, 0 disables proactive loop), `outbound_rate` (actions/sec), `outbound_burst`.

**[security]** — `vault_path`, `encrypted_session` (bool), `session_path`.

**[safety]** — `rate_limit_per_chat`, `rate_limit_global`, `rate_limit_burst`.

## Tools

`send_message`, `reply_message`, `forward_message`, `delete_message`, `get_messages`, `search_messages`, `get_dialogs`, `get_chat_info`, `get_chat_members`, `get_me`, `join_chat`, `leave_chat`, `send_file`

Set `tools` in config to a list to whitelist, or leave it out to enable all of them.

## Vault CLI

```bash
gramwork vault init          # create a new vault
gramwork vault set KEY VAL   # store a secret
gramwork vault get KEY       # print a secret
gramwork vault list          # list all keys
```

## Handler mode

You don't have to use autonomous mode. gramwork works fine as a plain handler framework:

```python
from gramwork import GramWork

app = GramWork(config_path="config.toml")

@app.on_message(pattern=r"/ping")
async def ping(ctx):
    await ctx.reply("pong!")

app.run()
```

## Env var overrides

Everything in the config can be overridden with env vars: `GRAMWORK_API_ID`, `GRAMWORK_API_HASH`, `GRAMWORK_LLM_PROVIDER`, `GRAMWORK_LLM_MODEL`, `GRAMWORK_AUTONOMOUS`, `GRAMWORK_MASTER_PASSWORD`, etc.

## License

MIT

## Author

poptye — poptye@proton.me
