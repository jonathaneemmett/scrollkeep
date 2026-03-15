import openai


class OpenAIProvider:
    def __init__(self, api_key: str) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self, messages: list[dict[str, str]], model: str = "gpt-4o"
    ) -> str:
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content
        if content is None:
            return ""
        return content
