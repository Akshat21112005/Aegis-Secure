from __future__ import annotations

from typing import Any

from playwright.async_api import Page


_PERMISSIONS_SCRIPT = """
async () => {
    const permissionNames = [
        "camera",
        "microphone",
        "geolocation",
        "notifications",
        "clipboard-read",
        "clipboard-write",
        "persistent-storage",
        "background-sync",
        "midi",
        "payment-handler",
    ];

    const permission_states = {};
    for (const name of permissionNames) {
        try {
            const result = await navigator.permissions.query({ name });
            permission_states[name] = result.state;
        } catch (error) {
            permission_states[name] = "unsupported";
        }
    }

    const api_availability = {
        bluetooth: !!navigator.bluetooth,
        usb: !!navigator.usb,
        serial: !!navigator.serial,
        nfc: !!navigator.nfc,
        geolocation: !!navigator.geolocation,
        media_devices: !!navigator.mediaDevices,
        service_worker: !!navigator.serviceWorker,
        clipboard: !!navigator.clipboard,
        credentials: !!navigator.credentials,
        wake_lock: !!navigator.wakeLock,
    };

    const granted_count = Object.values(permission_states).filter(
        (state) => state === "granted"
    ).length;
    const prompt_count = Object.values(permission_states).filter(
        (state) => state === "prompt"
    ).length;
    const denied_count = Object.values(permission_states).filter(
        (state) => state === "denied"
    ).length;

    return {
        permission_states,
        api_availability,
        summary: {
            granted_count,
            prompt_count,
            denied_count,
            unsupported_count: Object.values(permission_states).filter(
                (state) => state === "unsupported"
            ).length,
        },
    };
}
"""


async def collect_permissions(page: Page) -> dict[str, Any]:
    """Collect browser permission states and related API availability."""

    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)
    return await page.evaluate(_PERMISSIONS_SCRIPT)
