# M5Stack compatibility protocol

设备先由家长账号注册，随后调用 bootstrap 获取能力和音频端点。每次交互按 `IDLE → LISTENING → UPLOADING → THINKING → SPEAKING → IDLE` 上报 heartbeat。V1 模拟器使用家长 Cookie；真实固件应改用一次性配对码换取独立、可撤销的设备凭证。

