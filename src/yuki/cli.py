"""异步命令行交互循环。"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from .core.app import App
from .providers import ChatChunk
from .skills.package_manager import LocalDirSource, ZipSource

EXIT_COMMANDS = {"exit", "quit", "q", "退出"}

THINK_TAGS = ("<think>", "</think>")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def clean_content(text: str, pending: str) -> tuple[str, str, bool]:
    """去掉内容流里的 think 标签，返回清理文本、待续标签、是否出现过标签。"""
    combined = pending + text
    saw_tag = any(tag in combined for tag in THINK_TAGS)
    for tag in THINK_TAGS:
        combined = combined.replace(tag, "")
    for tag in THINK_TAGS:
        for size in range(len(tag) - 1, 0, -1):
            if combined.endswith(tag[:size]):
                return combined[:-size], combined[-size:], saw_tag
    return combined, "", saw_tag


def split_sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_SPLIT.split(text) if part]


@dataclass
class Response:
    """异步流式输出的惰性收集器，渲染时逐块消费并收集。"""

    stream: AsyncIterator[ChatChunk]
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)
    _iterator: AsyncIterator[ChatChunk] = field(init=False, repr=False)
    _finished: bool = field(default=False, init=False, repr=False)
    _content_pending: str = field(default="", init=False, repr=False)
    _content_buffer: str = field(default="", init=False, repr=False)
    _last_sentence: str = field(default="", init=False, repr=False)
    _flush_pending: str = field(default="", init=False, repr=False)
    _content_saw_think_tag: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        self._iterator = self.stream.__aiter__()

    async def next_event(self) -> Optional[dict[str, Any]]:
        if self._finished:
            return self._flush_content()
        try:
            chunk = await self._iterator.__anext__()
        except StopAsyncIteration:
            self._finished = True
            return self._flush_content()

        event = None
        if chunk.thinking and chunk.thinking.strip():
            self.thinking += chunk.thinking
            event = {"type": "thinking", "text": chunk.thinking.rstrip()}
        elif chunk.tool_calls:
            self.tool_calls.extend(chunk.tool_calls)
            event = {"type": "tool_calls", "calls": list(chunk.tool_calls)}
        elif chunk.content is not None:
            clean, pending, saw_tag = clean_content(chunk.content, self._content_pending)
            self._content_pending = pending
            if saw_tag:
                self._content_saw_think_tag = True
            self._content_buffer += clean
            event = self._emit_content()

        if chunk.done:
            self._finished = True
            if self._content_buffer:
                self._flush_pending = self._content_buffer
                self._content_buffer = ""
            await self._drain()
        if event is None and not self._finished:
            return await self.next_event()
        if event is None:
            return self._flush_content()
        return event

    async def _drain(self) -> None:
        """排空剩余流，避免异步生成器被 GC 关闭时报错。"""
        try:
            while True:
                await self._iterator.__anext__()
        except StopAsyncIteration:
            pass

    def _emit_content(self) -> Optional[dict[str, Any]]:
        sentences = split_sentences(self._content_buffer)
        self._content_buffer = ""
        emitted = []
        for sentence in sentences:
            key = sentence.strip()
            if not key:
                continue
            if self._content_saw_think_tag and key == self._last_sentence:
                continue
            self._last_sentence = key
            self.content += sentence
            emitted.append(sentence)
        if not emitted:
            return None
        return {"type": "content", "text": "".join(emitted)}

    def _flush_content(self) -> Optional[dict[str, Any]]:
        text = self._flush_pending
        self._flush_pending = ""
        if not text or (
            self._content_saw_think_tag and text.strip() == self._last_sentence
        ):
            return None
        self._last_sentence = text.strip()
        self.content += text
        return {"type": "content", "text": text}


def output_response(stream: AsyncIterator[ChatChunk]) -> Response:
    return Response(stream)


async def render_response(out: Response) -> list[Any]:
    state = "initial"

    def switch_state(current_state, next_state, label):
        if current_state != next_state:
            if current_state != "initial":
                print()
            print(label, end="")
        return next_state

    while True:
        event = await out.next_event()
        if event is None:
            break
        if event["type"] == "thinking":
            state = switch_state(state, "thinking", "思考：")
            print(event["text"], end="", flush=True)
        elif event["type"] == "tool_calls":
            state = switch_state(state, "tool_calling", "工具调用：")
            print(event["calls"], end="", flush=True)
        elif event["type"] == "content":
            state = switch_state(state, "ans", "回答：")
            print(event["text"], end="", flush=True)
    print()
    return out.tool_calls


async def cli_approver(name: str, _arguments: dict[str, Any]) -> str:
    answer = await asyncio.to_thread(
        input,
        f"工具 {name} 需要审批 (y / ya / y <分钟> / n)：",
    )
    return answer.strip()


async def handle_pkg(app: App, arg: str) -> None:
    parts = arg.split(maxsplit=1)
    sub = parts[0] if parts else ""
    ref = parts[1].strip() if len(parts) > 1 else ""

    if sub == "install":
        if not ref:
            print("用法：/pkg install <目录|zip>")
            return
        source = ZipSource() if ref.lower().endswith(".zip") else LocalDirSource()
        try:
            info = await app.package_manager.install(source, ref)
            print(f"已安装：{info.id} {info.version}")
            app.registry.scan_packages(
                app.settings.packages_dir,
                available=app.settings.packages or None,
            )
        except Exception as err:
            print(f"安装失败：{err}")
    elif sub == "remove":
        if not ref:
            print("用法：/pkg remove <id>")
            return
        try:
            app.package_manager.remove(ref)
            print(f"已卸载：{ref}")
            app.registry.scan_packages(
                app.settings.packages_dir,
                available=app.settings.packages or None,
            )
        except Exception as err:
            print(f"卸载失败：{err}")
    elif sub == "list":
        infos = app.package_manager.list_installed()
        if not infos:
            print("暂无已安装包")
            return
        for info in infos:
            print(f"{info.id} {info.version} {info.source}")
    else:
        print("用法：/pkg install <目录|zip> | /pkg remove <id> | /pkg list")


async def handle_command(app: App, line: str) -> bool:
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/save":
        if not arg:
            print("用法：/save <名字>")
            return True
        app.session.name = arg
        await asyncio.to_thread(app.store.save, app.session)
        print(f"会话已保存：{arg}")
    elif cmd == "/load":
        if not arg:
            print("用法：/load <名字>")
            return True
        meta = None
        for item in app.store.list_sessions():
            if item.name == arg:
                meta = item
                break
        if meta is None:
            print(f"找不到会话：{arg}")
            return True
        session = await asyncio.to_thread(app.store.load, meta.session_id)
        if session is None:
            print(f"会话文件缺失：{arg}")
            return True
        app.session = session
        app.agent.switch_session(session)
        print(f"已加载会话：{arg}")
    elif cmd == "/sessions":
        metas = app.store.list_sessions()
        if not metas:
            print("暂无已保存会话")
            return True
        for meta in metas:
            print(f"{meta.name}  {meta.updated_at}")
    elif cmd == "/new":
        app.agent.switch_session(app.store.create())
        print("已开始新会话")
    elif cmd == "/reload":
        await app.reload()
        print("配置已热加载")
    elif cmd == "/pkg":
        await handle_pkg(app, arg)
    else:
        print(f"未知命令：{cmd}")
    return True


async def run(app: App) -> None:
    while True:
        raw = await asyncio.to_thread(input, "user：")
        line = raw.strip()
        if not line:
            continue
        if line.lower() in EXIT_COMMANDS:
            break
        if line.startswith("/"):
            await handle_command(app, line)
            continue

        active_packages = app.agent.registry.active_packages
        out = output_response(app.agent.send_message(line))
        tool_calls = await render_response(out)
        while tool_calls:
            results = await app.agent.execute_tool_calls(tool_calls)
            for result in results:
                print(f"工具结果：{result['content']}")
            out = output_response(app.agent.continue_with_tools(tool_calls, results))
            tool_calls = await render_response(out)
        changed = await app.agent.restore_packages(active_packages)
        if changed:
            print(f"外置包已还原：{'、'.join(changed)}")
        if out.content:
            await app.agent.remember(line, out.content)
            app.agent.memory.append({"role": "assistant", "content": out.content})
