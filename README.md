# astrbot_plugin_mimo_tts_voiceclone

基于小米 Mimo-v2.5-tts-voiceclone 的声音克隆 TTS 插件，用于 AstrBot 聊天机器人。

MiMo 正在进行**百万亿 Token 创造者激励计划**（申请网址：[https://100t.xiaomimimo.com](https://100t.xiaomimimo.com)），2026/04/28 - 2026/05/28 期间，可**免费领取** 200M - 1600M 额度，尽情使用 Mimo-v2.5-tts-voiceclone 的声音克隆功能吧 ~

## 功能特性

- 支持用户上传参考音频进行声音克隆
- 可配置触发声音克隆的概率
- 支持多种音频格式输出（WAV、MP3、OGG、FLAC）
- 可调节语音播放速度
- 仅对 LLM 生成的回复进行处理，其他插件传入的回复不会触发 TTS

## 配置说明

在 AstrBot WebUI 的插件配置页面中，您可以配置以下参数：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API Key | Mimo TTS 服务的 API 密钥 | - |
| API Base URL | Mimo TTS API 的基础 URL | https://api.xiaomi.com/v1 |
| 触发概率 | LLM 回复触发声音克隆的概率 (0-1) | 0.5 |
| 参考音频 | 上传用于声音克隆的参考音频文件 | - |
| 模型名称 | 使用的 TTS 模型名称 | mimo-v2.5-tts-voiceclone |
| 输出格式 | 生成的音频文件格式 | wav |
| 语音速度 | 语音播放速度 (0.5-2.0) | 1.0 |
| 最大文本长度 | 单次 TTS 转换的最大文本长度 | 500 |

## 使用方法

1. 在 AstrBot WebUI 中安装此插件
2. 配置 Mimo TTS 的 API Key 和 Base URL
3. 上传参考音频文件：
   - 支持 WAV、MP3、FLAC、OGG 格式
   - 时长需要在 5 - 30s，无背景音干扰
4. 调整触发概率和其他参数
5. 保存配置并启用插件

## 工作原理

1. 插件监听 LLM 生成的文字回复
2. 根据配置的概率决定是否触发声音克隆
3. 如果触发，调用 MiMo-v2.5-TTS-VoiceClone TTS API 将文字转换为语音
4. 用生成的语音替换原始文字回复
5. 如果 TTS 失败，保留原始文字回复

## 依赖要求

- Python >= 3.10
- aiohttp >= 3.8.0
- AstrBot >= 4.0.0

## 许可证

AGPL-3.0 License
