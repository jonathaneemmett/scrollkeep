import anthropic
from anthropic.types import MessageParam, TextBlock


class AnthropicProvider:
    def __init__(self, api_key: str) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
    ) -> str:
        response = await self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[MessageParam(**m) for m in messages],  # type: ignore[typeddict-item]
        )
        block = response.content[0]
        assert isinstance(block, TextBlock)
        return block.text
