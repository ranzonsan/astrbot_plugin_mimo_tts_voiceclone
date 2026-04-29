import base64
import os
import random
import tempfile

import aiohttp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Record
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path


@register(
    "astrbot_plugin_mimo_tts_voiceclone",
    "AstrBot Plugin Developer",
    "基于小米 Mimo-v2.5-tts-voiceclone 的声音克隆 TTS 插件",
    "v1.0.0",
)
class MimoTTSVoiceClonePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.xiaomimimo.com/v1")
        self.trigger_probability = config.get("trigger_probability", 0.5)
        self.model_name = config.get("model_name", "mimo-v2.5-tts-voiceclone")
        self.output_format = config.get("output_format", "wav")
        self.voice_speed = config.get("voice_speed", 1.0)
        self.max_text_length = config.get("max_text_length", 500)
        self.reference_audio_path = None
        self.reference_audio_base64 = None

        self._setup_reference_audio()

    def _setup_reference_audio(self):
        reference_audio = self.config.get("reference_audio", [])
        if reference_audio and len(reference_audio) > 0:
            relative_path = reference_audio[0]
            plugin_data_root = get_astrbot_plugin_data_path()
            plugin_name = "astrbot_plugin_mimo_tts_voiceclone"
            self.reference_audio_path = os.path.join(plugin_data_root, plugin_name, relative_path)
            self.reference_audio_path = os.path.normpath(self.reference_audio_path)
            logger.info(f"[MimoTTS] 参考音频相对路径: {relative_path}")
            logger.info(f"[MimoTTS] 插件数据根目录: {plugin_data_root}")
            logger.info(f"[MimoTTS] 参考音频完整路径: {self.reference_audio_path}")
            logger.info(f"[MimoTTS] 文件是否存在: {os.path.exists(self.reference_audio_path)}")
            if os.path.exists(self.reference_audio_path):
                try:
                    with open(self.reference_audio_path, "rb") as f:
                        audio_bytes = f.read()
                    self.reference_audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    logger.info(f"[MimoTTS] 参考音频已加载并编码，大小: {len(self.reference_audio_base64)} bytes")
                except Exception as e:
                    logger.error(f"[MimoTTS] 读取参考音频失败: {e}")
        else:
            logger.warning("[MimoTTS] 未上传参考音频文件，声音克隆功能将不可用")

    async def initialize(self):
        logger.info("[MimoTTS] 插件初始化中...")
        logger.info(f"[MimoTTS] API Key 配置: {'已配置' if self.api_key else '未配置'}")
        logger.info(f"[MimoTTS] 参考音频: {'已上传' if self.reference_audio_base64 else '未上传'}")
        logger.info(f"[MimoTTS] 触发概率: {self.trigger_probability}")
        logger.info(f"[MimoTTS] Base URL: {self.base_url}")
        logger.info(f"[MimoTTS] 模型名称: {self.model_name}")
        if not self.api_key:
            logger.warning("[MimoTTS] 未配置 API Key，声音克隆功能将不可用")

    def _should_trigger_tts(self) -> bool:
        if not self.api_key:
            logger.debug("[MimoTTS] 未配置 API Key，跳过 TTS")
            return False
        if not self.reference_audio_base64:
            logger.debug("[MimoTTS] 未上传参考音频，跳过 TTS")
            return False
        random_value = random.random()
        should_trigger = random_value < self.trigger_probability
        # logger.debug(f"[MimoTTS] 概率判定: random={random_value:.4f}, threshold={self.trigger_probability}, trigger={should_trigger}")
        return should_trigger

    def _truncate_text(self, text: str) -> str:
        if len(text) > self.max_text_length:
            logger.warning(f"[MimoTTS] 文本长度 {len(text)} 超过限制 {self.max_text_length}，将截断")
            return text[:self.max_text_length]
        return text

    def _get_mime_type(self) -> str:
        if self.reference_audio_path:
            ext = os.path.splitext(self.reference_audio_path)[1].lower()
            if ext == ".mp3":
                return "audio/mpeg"
            elif ext == ".wav":
                return "audio/wav"
        return "audio/mpeg"

    async def _call_mimo_tts(self, text: str) -> bytes | None:
        truncated_text = self._truncate_text(text)
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        # logger.info(f"[MimoTTS] ====== 开始调用 TTS API ======")
        # logger.info(f"[MimoTTS] API URL: {url}")
        # logger.info(f"[MimoTTS] 模型: {self.model_name}")
        # logger.info(f"[MimoTTS] 文本内容: {truncated_text[:100]}...")
        logger.info(f"[MimoTTS] 开始调用 TTS API，API URL: {url}，模型: {self.model_name}")

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        mime_type = self._get_mime_type()
        voice_value = f"data:{mime_type};base64,{self.reference_audio_base64}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": truncated_text}
            ],
            "audio": {
                "format": self.output_format,
                "voice": voice_value
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.info("[MimoTTS] 发送 TTS 请求...")
                async with session.post(
                    url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            message = result["choices"][0].get("message", {})
                            audio_data = message.get("audio", {})
                            if audio_data and "data" in audio_data:
                                audio_bytes = base64.b64decode(audio_data["data"])
                                logger.info(f"[MimoTTS] TTS 转换成功，音频大小: {len(audio_bytes)} bytes")
                                return audio_bytes
                            else:
                                logger.error(f"[MimoTTS] 响应中没有音频数据: {result}")
                                return None
                        else:
                            logger.error(f"[MimoTTS] 响应格式错误: {result}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"[MimoTTS] TTS API 请求失败: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"[MimoTTS] TTS API 请求异常: {e}")
            return None

    async def _save_audio_to_temp_file(self, audio_data: bytes) -> str | None:
        try:
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"mimo_tts_{os.urandom(8).hex()}.{self.output_format}")
            with open(temp_file, "wb") as f:
                f.write(audio_data)
            logger.info(f"[MimoTTS] 音频已保存到临时文件: {temp_file}")
            return temp_file
        except Exception as e:
            logger.error(f"[MimoTTS] 保存音频文件失败: {e}")
            return None

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        logger.info("[MimoTTS] on_decorating_result 钩子被触发")

        result = event.get_result()
        if not result:
            # logger.debug("[MimoTTS] result 为空，跳过")
            return

        # logger.info(f"[MimoTTS] result 类型: {type(result).__name__}")
        # logger.info(f"[MimoTTS] result_content_type: {result.result_content_type}")
        # logger.info(f"[MimoTTS] is_llm_result: {result.is_llm_result()}")

        if not result.is_llm_result():
            logger.info("[MimoTTS] 非 LLM 回复，跳过 TTS 处理")
            return

        # logger.info("[MimoTTS] 检测到 LLM 回复，检查是否触发 TTS...")

        if not self._should_trigger_tts():
            # logger.info("[MimoTTS] 概率判定未触发 TTS")
            return

        text_content = ""
        for component in result.chain:
            if isinstance(component, Plain):
                text_content += component.text

        if not text_content.strip():
            logger.warning("[MimoTTS] 文本内容为空，跳过 TTS")
            return

        # logger.info(f"[MimoTTS] ====== 开始声音克隆转换 ======")
        # logger.info(f"[MimoTTS] 原始文本: {text_content[:200]}...")

        audio_data = await self._call_mimo_tts(text_content)

        if audio_data:
            temp_file = await self._save_audio_to_temp_file(audio_data)
            if temp_file:
                result.chain.clear()
                result.chain.append(Record(file=temp_file, url=temp_file))
                # logger.info("[MimoTTS] ====== 声音克隆转换完成 ======")
                logger.info("[MimoTTS] 声音克隆转换完成，已将文字回复替换为语音")
            else:
                logger.warning("[MimoTTS] 保存音频文件失败，保留原始文字回复")
        else:
            logger.warning("[MimoTTS] TTS 转换失败，保留原始文字回复")

    async def terminate(self):
        logger.info("[MimoTTS] Mimo TTS 声音克隆插件已停止")
