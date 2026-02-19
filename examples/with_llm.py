"""Example with LLM provider — shows how to wire up an AI backend."""

from gramwork import ChatMessage, EventContext, GramWork, Role
from gramwork.llm.base import LLMProvider


class MyLLMProvider:
    """Example stub — replace with your real LLM provider."""

    async def complete(self, messages: list[ChatMessage]) -> ChatMessage:
        # Replace this with your actual LLM call
        return ChatMessage(Role.ASSISTANT, "I'm a stub LLM response!")

    async def stream(self, messages: list[ChatMessage]):
        yield "I'm "
        yield "streaming!"


app = GramWork(config_path="config.toml", llm=MyLLMProvider())


@app.on_message(pattern=r"/ask\s+(.*)")
async def ask(ctx: EventContext) -> None:
    """Forward user question to LLM and reply with the answer."""
    import re

    match = re.match(r"/ask\s+(.*)", ctx.text)
    if not match:
        return

    question = match.group(1)
    await ctx.save_turn(Role.USER, question)

    messages = [
        ChatMessage(Role.SYSTEM, "You are a helpful Telegram assistant."),
        ChatMessage(Role.USER, question),
    ]
    response = await ctx.llm_complete(messages)
    await ctx.save_turn(Role.ASSISTANT, response.content)
    await ctx.reply(response.content)


if __name__ == "__main__":
    app.run()
