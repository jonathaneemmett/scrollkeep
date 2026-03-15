from typing import Any, Protocol, runtime_checkable

from mcp_server.llm.types import LLMResponse, ToolSchema


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, messages: list[dict[str, str]], model: str) -> str: ... 
                                                                                    
    async def complete_with_tools(                                                   
        self,                                                                        
        messages: list[dict[str, Any]],                                              
        model: str,                                       
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse: ...  