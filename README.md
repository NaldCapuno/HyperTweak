# HyperTweak (Tkinter + ADB)

## Setup

1. Enable **USB debugging** (and **USB debugging (Security settings)**) on your phone.
2. Plug in via USB and accept the **Allow USB debugging** prompt.
3. Download and unzip the latest release and run `HyperTweak.exe`.

## Overview

- **Current Device Settings** — Tabs for `system`, `secure`, `global`, and `props` showing `key = value` pairs. Supports **Refresh**, **Save**, and **Load** of the full snapshot.

  > **Note (props tab):**  
  > The `ro.surface_flinger.supports_background_blur` property tells Android whether the GPU is capable of rendering system blur.

- **Quick Toggles** — Remove animations (on/off) and Recents style (Vertically / Horizontally / Stacked). Uses the device’s current values and applies changes immediately.
- **Advanced Settings** — Device Level List, Computility, Advanced Visual Release, Advanced Textures, Animation, Temp Limit. Use **Apply Settings** to push changes and **Restore previous settings** to revert the last apply.
- **Command Console** — Run custom ADB shell commands.

## Restore previous settings

- When you click **Apply Settings**, HyperTweak first snapshots the current advanced-related values on the device.
- A **Restore previous settings** button then appears in the footer.
- Clicking it repopulates the Advanced Settings inputs from that snapshot and re-applies those values to the device (Quick Toggles are not affected).

## Command Console

The **Command Console** tab on the right lets you run **ADB shell commands** on the connected device.

- Top box: **command input**
- Bottom area: **read-only output**

### Basic command format

Type exactly what you would enter **after** `adb shell`:

```text
<command> [arg1] [arg2] ...
```

**Don’t** include `adb shell` itself.

Examples:

```text
getprop ro.product.model
settings list system
settings get system deviceLevelList
settings put system deviceLevelList "v:1,c:1,g:1"
```

Each time you press **Run**:

- The previous output is cleared
- The command(s) run on the device
- The console shows `$ <command>` and its output

**Multiple commands:** Separate with `;` to run several in one go:

```text
getprop ro.product.model; settings list system; getprop persist.sys.background_blur_supported
```

### MIUI `service call` format (advanced)

On MIUI devices that support `miui.mqsas.IMQSNative`, you can set `persist.sys.*` props with:

```text
service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "<prop> <value>" s16 "/storage/emulated/0/log.txt" i32 600
```

Replace only `<prop> <value>`, for example:

```text
service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.computility.cpulevel 3" s16 "/storage/emulated/0/log.txt" i32 600
service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.advanced_visual_release 2" s16 "/storage/emulated/0/log.txt" i32 600
service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.background_blur_supported true" s16 "/storage/emulated/0/log.txt" i32 600
```
