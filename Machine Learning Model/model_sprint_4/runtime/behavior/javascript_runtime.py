from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page


@dataclass
class JavaScriptMonitor:
    console_logs: list[dict[str, Any]] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    dialog_events: list[dict[str, Any]] = field(default_factory=list)
    console_error_count: int = 0
    console_warning_count: int = 0
    installed: bool = False


async def install_javascript_monitoring(page: Page) -> JavaScriptMonitor:
    """Register runtime hooks and listeners before navigation."""

    monitor = JavaScriptMonitor()

    async def console_listener(message):
        try:
            monitor.console_logs.append(
                {
                    "type": message.type,
                    "text": message.text,
                    "location": message.location,
                }
            )
            if message.type == "error":
                monitor.console_error_count += 1
            elif message.type == "warning":
                monitor.console_warning_count += 1
        except Exception:
            pass

    async def page_error_listener(error):
        try:
            monitor.page_errors.append(str(error))
        except Exception:
            pass

    async def dialog_listener(dialog):
        try:
            monitor.dialog_events.append(
                {
                    "type": dialog.type,
                    "message": dialog.message,
                }
            )
            await dialog.dismiss()
        except Exception:
            pass

    page.on("console", console_listener)
    page.on("pageerror", page_error_listener)
    page.on("dialog", dialog_listener)

    for script in _INIT_SCRIPTS:
        await page.add_init_script(script)

    monitor.installed = True
    return monitor


async def collect_javascript(
    page: Page,
    monitor: JavaScriptMonitor | None = None,
    *,
    settle_ms: int = 3000,
) -> dict[str, Any]:
    """Collect browser runtime metrics after the page has loaded."""

    if monitor is None:
        monitor = await install_javascript_monitoring(page)

    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(settle_ms)

    dom_metrics = await page.evaluate(_DOM_METRICS_SCRIPT)
    runtime_metrics = await page.evaluate("() => window.__AEGIS__ || {}")
    browser_metrics = await page.evaluate(_BROWSER_METRICS_SCRIPT)

    return {
        "console_logs": monitor.console_logs[:120],
        "console_error_count": monitor.console_error_count,
        "console_warning_count": monitor.console_warning_count,
        "page_errors": monitor.page_errors[:40],
        "page_error_count": len(monitor.page_errors),
        "dialogs": monitor.dialog_events[:20],
        "dialog_count": len(monitor.dialog_events),
        "runtime_metrics": runtime_metrics,
        "dom_metrics": dom_metrics,
        "browser_metrics": browser_metrics,
    }


_INIT_SCRIPTS = [
    """
    (() => {
        window.__AEGIS__ = {
            eval_calls: 0,
            function_calls: 0,
            fetch_calls: 0,
            xhr_calls: 0,
            websocket_calls: 0,
            beacon_calls: 0,
            document_write_calls: 0,
            window_open_calls: 0,
            history_push_calls: 0,
            history_replace_calls: 0,
            clipboard_read_calls: 0,
            clipboard_write_calls: 0,
            atob_calls: 0,
            btoa_calls: 0,
            timeout_calls: 0,
            interval_calls: 0,
            post_message_calls: 0,
            dynamic_script_insertions: 0,
            mutation_count: 0,
        };
    })();
    """,
    """
    (() => {
        const oldEval = window.eval;
        window.eval = function (...args) {
            window.__AEGIS__.eval_calls++;
            return oldEval.apply(this, args);
        };
        const oldFunction = window.Function;
        window.Function = function (...args) {
            window.__AEGIS__.function_calls++;
            return oldFunction.apply(this, args);
        };
        const oldFetch = window.fetch;
        window.fetch = function (...args) {
            window.__AEGIS__.fetch_calls++;
            return oldFetch.apply(this, args);
        };
    })();
    """,
    """
    (() => {
        const oldOpen = window.open;
        window.open = function (...args) {
            window.__AEGIS__.window_open_calls++;
            return oldOpen.apply(this, args);
        };
        const oldWrite = document.write;
        document.write = function (...args) {
            window.__AEGIS__.document_write_calls++;
            return oldWrite.apply(this, args);
        };
        const oldPush = history.pushState;
        history.pushState = function (...args) {
            window.__AEGIS__.history_push_calls++;
            return oldPush.apply(this, args);
        };
        const oldReplace = history.replaceState;
        history.replaceState = function (...args) {
            window.__AEGIS__.history_replace_calls++;
            return oldReplace.apply(this, args);
        };
        const oldAtob = window.atob;
        window.atob = function (...args) {
            window.__AEGIS__.atob_calls++;
            return oldAtob.apply(this, args);
        };
        const oldBtoa = window.btoa;
        window.btoa = function (...args) {
            window.__AEGIS__.btoa_calls++;
            return oldBtoa.apply(this, args);
        };
    })();
    """,
    """
    (() => {
        const oldTimeout = window.setTimeout;
        window.setTimeout = function (...args) {
            window.__AEGIS__.timeout_calls++;
            return oldTimeout.apply(this, args);
        };
        const oldInterval = window.setInterval;
        window.setInterval = function (...args) {
            window.__AEGIS__.interval_calls++;
            return oldInterval.apply(this, args);
        };
        const oldPostMessage = window.postMessage;
        window.postMessage = function (...args) {
            window.__AEGIS__.post_message_calls++;
            return oldPostMessage.apply(this, args);
        };
    })();
    """,
    """
    (() => {
        const oldCreate = document.createElement;
        document.createElement = function (...args) {
            const element = oldCreate.apply(this, args);
            if (args.length > 0 && String(args[0]).toLowerCase() === "script") {
                window.__AEGIS__.dynamic_script_insertions++;
            }
            return element;
        };
    })();
    """,
    """
    (() => {
        const oldXHR = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function (...args) {
            window.__AEGIS__.xhr_calls++;
            return oldXHR.apply(this, args);
        };
        if (window.WebSocket) {
            const OldSocket = window.WebSocket;
            window.WebSocket = function (...args) {
                window.__AEGIS__.websocket_calls++;
                return new OldSocket(...args);
            };
            window.WebSocket.prototype = OldSocket.prototype;
        }
        if (navigator.sendBeacon) {
            const oldBeacon = navigator.sendBeacon.bind(navigator);
            navigator.sendBeacon = function (...args) {
                window.__AEGIS__.beacon_calls++;
                return oldBeacon(...args);
            };
        }
    })();
    """,
    """
    (() => {
        if (!navigator.clipboard) {
            return;
        }
        if (navigator.clipboard.readText) {
            const oldRead = navigator.clipboard.readText.bind(navigator.clipboard);
            navigator.clipboard.readText = function (...args) {
                window.__AEGIS__.clipboard_read_calls++;
                return oldRead(...args);
            };
        }
        if (navigator.clipboard.writeText) {
            const oldWrite = navigator.clipboard.writeText.bind(navigator.clipboard);
            navigator.clipboard.writeText = function (...args) {
                window.__AEGIS__.clipboard_write_calls++;
                return oldWrite(...args);
            };
        }
    })();
    """,
]

_DOM_METRICS_SCRIPT = """
() => ({
    script_count: document.scripts.length,
    inline_scripts: [...document.scripts].filter((script) => !script.src).length,
    external_scripts: [...document.scripts].filter((script) => script.src).length,
    iframe_count: document.querySelectorAll("iframe").length,
    form_count: document.forms.length,
    input_count: document.querySelectorAll("input").length,
    button_count: document.querySelectorAll("button").length,
    anchor_count: document.links.length,
    image_count: document.images.length,
    password_fields: document.querySelectorAll("input[type=password]").length,
    hidden_inputs: document.querySelectorAll("input[type=hidden]").length,
    title: document.title,
    ready_state: document.readyState,
})
"""

_BROWSER_METRICS_SCRIPT = """
() => ({
    cookies_enabled: navigator.cookieEnabled,
    language: navigator.language,
    platform: navigator.platform,
    user_agent: navigator.userAgent,
    online: navigator.onLine,
    hardware_threads: navigator.hardwareConcurrency,
    device_memory: navigator.deviceMemory || null,
})
"""
