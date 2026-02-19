"""Minimal gramwork example — responds to /ping."""

from gramwork import GramWork

app = GramWork(config_path="config.toml")


@app.on_message(pattern=r"/ping")
async def ping(ctx):
    await ctx.reply("pong!")


@app.on_message(pattern=r"/echo\s+(.*)")
async def echo(ctx):
    # Echo back everything after /echo
    import re

    match = re.match(r"/echo\s+(.*)", ctx.text)
    if match:
        await ctx.reply(match.group(1))


if __name__ == "__main__":
    app.run()
