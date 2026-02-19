"""Example using multiple plugins and middleware."""

from gramwork import EventContext, GramWork, RateLimitMiddleware, Router
from gramwork.safety.filters import ContentFilterMiddleware

app = GramWork(config_path="config.toml")

# Add rate limiting
app.add_middleware(RateLimitMiddleware(per_chat_rate=3.0, global_rate=20.0))

# Add content filter
content_filter = ContentFilterMiddleware(auto_delete=True)
content_filter.add_patterns("spam", [r"buy now", r"click here", r"free money"])
app.add_middleware(content_filter)

# Custom router for admin commands
admin_router = Router()


@admin_router.on_message(pattern=r"/ban")
async def ban_user(ctx: EventContext) -> None:
    await ctx.reply("Ban functionality — implement with Telethon client API.")


@admin_router.on_message(pattern=r"/stats")
async def stats(ctx: EventContext) -> None:
    await ctx.reply("Stats functionality — query your state backend here.")


app.include_router(admin_router)


@app.on_message(pattern=r"/ping")
async def ping(ctx: EventContext) -> None:
    await ctx.reply("pong!")


if __name__ == "__main__":
    app.run()
