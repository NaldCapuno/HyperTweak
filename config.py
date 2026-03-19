from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettingsPayload:
    v: int
    c: int
    g: int
    cpulevel: int
    gpulevel: int
    advanced_visual_release: int
    temp_limit_enabled: bool
    temp_limit_bottom: int
    temp_limit_ceiling: int
    miui_home_animation: str
    recents_style: str
    background_blur_supported: str


@dataclass(frozen=True)
class ApplySelection:
    device_level_list: bool
    computility: bool
    advanced_visual_release: bool
    temp_limit: bool
    miui_home_animation: bool
    recents_style: bool
    background_blur_supported: bool


def build_shell_commands(payload: SettingsPayload, selection: ApplySelection) -> list[str]:
    def put(key: str, value: Any) -> str:
        return f"settings put system {key} {value}"

    def put_global(key: str, value: Any) -> str:
        return f"settings put global {key} {value}"

    def mqsas_setprop(prop_and_value: str) -> str:
        return (
            'service call miui.mqsas.IMQSNative 21 '
            'i32 1 s16 "setprop" i32 1 '
            f's16 "{prop_and_value}" '
            's16 "/storage/emulated/0/log.txt" i32 600'
        )

    device_level_list = f"v:{payload.v},c:{payload.c},g:{payload.g}"

    recents_style_map = {"Vertically": 0, "Horizontally": 1, "Stacked": 2}
    recents_style_value = recents_style_map.get(str(payload.recents_style), payload.recents_style)

    home_anim_map = {"Relaxed": 0, "Balanced": 1, "Fast": 2}
    home_anim_value = home_anim_map.get(str(payload.miui_home_animation), payload.miui_home_animation)

    cmds: list[str] = []

    if selection.device_level_list:
        cmds.append(put("deviceLevelList", device_level_list))

    if selection.computility:
        cmds.append(mqsas_setprop(f"persist.sys.computility.cpulevel {payload.cpulevel}"))
        cmds.append(mqsas_setprop(f"persist.sys.computility.gpulevel {payload.gpulevel}"))

    if selection.advanced_visual_release:
        cmds.append(mqsas_setprop(f"persist.sys.advanced_visual_release {payload.advanced_visual_release}"))

    if selection.temp_limit:
        cmds.append(f"rt_enable_templimit {1 if payload.temp_limit_enabled else 0}")
        cmds.append(put("rt_templimit_bottom", payload.temp_limit_bottom))
        cmds.append(put("rt_templimit_ceiling", payload.temp_limit_ceiling))

    if selection.miui_home_animation:
        cmds.append(put("miui_home_animation_rate", home_anim_value))

    if selection.recents_style:
        cmds.append(put_global("task_stack_view_layout_style", recents_style_value))

    if selection.background_blur_supported:
        raw = str(payload.background_blur_supported).strip().lower()
        blur_value = "true" if raw in ("enabled", "true", "1") else "false"
        cmds.append(mqsas_setprop(f"persist.sys.background_blur_supported {blur_value}"))

    return cmds
