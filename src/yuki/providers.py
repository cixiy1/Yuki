"""Yuki 示例内置的 provider 实现：转译为内核 Provider 抽象。"""

import json
import socket
import subprocess
import sys
import time
from typing import Any, AsyncIterator, Mapping, Optional, Sequence, cast

import ollama

from yuki_kernel.config import Settings
from yuki_kernel.providers import register_provider
from yuki_kernel.providers.base import ChatChunk, Provider

ollama_proc: Optional[subprocess.Popen] = None


def is_ollama_running(host: str, port: int, timeout: float = 1) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def start_ollama_service(host: str = "127.0.0.1", port: int = 11434) -> bool:
    if is_ollama_running(host, port):
        print("Ollama 服务已运行，无需启动")
        return True
    print("未检测到Ollama服务，正在启动...")
    global ollama_proc
    creation_flags = {"creation_flags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    ollama_proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **creation_flags,
    )
    time.sleep(2)
    print("Ollama 服务已启动")
    return True


def stop_ollama_service() -> bool:
    global ollama_proc
    if ollama_proc is None:
        return False
    print("正在关闭Ollama服务...")
    ollama_proc.terminate()
    try:
        ollama_proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        ollama_proc.kill()
        ollama_proc.wait()
    ollama_proc = None
    print("Ollama服务已关闭")
    return True


class OllamaProvider(Provider):
    async def start(self) -> bool:
        return start_ollama_service(self.settings.ollama_host, self.settings.ollama_port)

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        kwargs.setdefault("think", self.settings.think)
        # noinspection HttpUrlsUsage
        client = ollama.AsyncClient(
            host=f"http://{self.settings.ollama_host}:{self.settings.ollama_port}"
        )
        stream = await client.chat(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            msg = chunk.message
            yield ChatChunk(
                thinking=msg.thinking,
                content=msg.content,
                tool_calls=list(msg.tool_calls or []),
                done=bool(chunk.done),
            )

    async def close(self, skip_unload: bool = False):
        if not skip_unload:
            try:
                # noinspection HttpUrlsUsage
                client = ollama.AsyncClient(
                    host=f"http://{self.settings.ollama_host}:{self.settings.ollama_port}"
                )
                await client.generate(model=self.model, prompt="", keep_alive="0s")
                print("模型已回收")
            except Exception as err:
                print("模型回收失败：", err)
        stop_ollama_service()

    def build_tool_messages(
        self,
        tool_calls: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assistant = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": call["name"], "arguments": call["arguments"]}}
                for call in tool_calls
            ],
        }
        tool_messages = [{"role": "tool", "content": result["content"]} for result in results]
        return [assistant] + tool_messages


class ApiProvider(Provider):
    def __init__(
        self,
        model: str,
        settings: Settings,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(model, settings)
        try:
            from openai import AsyncOpenAI
        except ImportError as err:
            raise ImportError("ApiProvider 需要安装 openai，请先执行 pip install openai") from err
        self.client = AsyncOpenAI(
            api_key=api_key or self.settings.openai_api_key,
            base_url=base_url or self.settings.openai_base_url,
        )

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        kwargs.pop("stream", None)
        if self.settings.think:
            extra_body = kwargs.setdefault("extra_body", {})
            extra_body.setdefault("thinking", {"type": "enabled"})
        stream = cast(
            Any,
            await self.client.chat.completions.create(
                model=cast(Any, self.model),
                messages=cast(Any, messages),
                tools=cast(Any, tools),
                stream=True,
                **kwargs,
            ),
        )
        try:
            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                if delta is None:
                    continue
                thinking = getattr(delta, "reasoning_content", None) or getattr(delta, "thinking", None)
                yield ChatChunk(
                    thinking=thinking,
                    content=getattr(delta, "content", None),
                    tool_calls=list(getattr(delta, "tool_calls", None) or []),
                    done=bool(getattr(choice, "finish_reason", False)),
                )
        finally:
            try:
                await stream.close()
            except (AttributeError, RuntimeError, OSError):
                pass

    async def close(self, skip_unload: bool = False):
        await self.client.close()

    def build_tool_messages(
        self,
        tool_calls: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assistant = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call.get("id") or f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
                for index, call in enumerate(tool_calls)
            ],
        }
        tool_messages = [
            {
                "role": "tool",
                "tool_call_id": call.get("id") or f"call_{index}",
                "content": result["content"],
            }
            for index, (call, result) in enumerate(zip(tool_calls, results))
        ]
        return [assistant] + tool_messages


def register_yuki_providers() -> None:
    register_provider("ollama", OllamaProvider)
    register_provider("api", ApiProvider)
