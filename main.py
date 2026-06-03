import asyncio
import base64
import os
import random
import tempfile

import aiohttp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Record, Reply
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path


PLUGIN_NAME = "astrbot_plugin_mimo_tts_voiceclone"


@register(
    PLUGIN_NAME,
    "AstrBot Plugin Developer",
    "基于小米 Mimo-v2.5-tts-voiceclone 的声音克隆 TTS 插件",
    "v1.2.4",
)
class MimoTTSVoiceClonePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.plugin_data_root = get_astrbot_plugin_data_path()
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.xiaomimimo.com/v1")
        self.trigger_probability = config.get("trigger_probability", 0.5)
        self.model_name = config.get("model_name", "mimo-v2.5-tts-voiceclone")
        self.output_format = config.get("output_format", "wav")
        self.voice_speed = config.get("voice_speed", 1.0)
        self.max_text_length = config.get("max_text_length", 500)
        self.reference_audio_path = None
        self.reference_audio_base64 = config.get("reference_audio_base64", "")
        self.default_reference_audio = None
        self.bot_reference_audio_files = {}
        self.bot_reference_audios = {}

        # self._setup_reference_audio()
        # self._setup_bot_reference_audio_files()
        # self._setup_bot_reference_audios()

    # def _get_first_uploaded_file(self, file_config) -> str:
    #     if isinstance(file_config, list):
    #         if not file_config:
    #             return ""
    #         file_config = file_config[0]
    #     if file_config is None:
    #         return ""
    #     return str(file_config).strip()
    #
    # def _resolve_audio_path(self, relative_path: str) -> str:
    #     return os.path.normpath(os.path.join(self.plugin_data_root, PLUGIN_NAME, relative_path))
    #
    # def _get_uploaded_files(self, file_config) -> list[str]:
    #     if not isinstance(file_config, list):
    #         file_config = [file_config]
    #     files = []
    #     for item in file_config:
    #         if item is None:
    #             continue
    #         relative_path = str(item).strip().replace("\\", "/")
    #         if relative_path:
    #             files.append(relative_path)
    #     return files
    #
    # def _load_reference_audio(self, file_config, label: str, warn_if_missing: bool = True) -> dict | None:
    #     relative_path = self._get_first_uploaded_file(file_config)
    #     if not relative_path:
    #         if warn_if_missing:
    #             logger.warning(f"[MimoTTS] 未上传{label}，声音克隆功能将不可用")
    #         return None
    #
    #     audio_path = self._resolve_audio_path(relative_path)
    #     logger.info(f"[MimoTTS] {label}相对路径: {relative_path}")
    #     logger.info(f"[MimoTTS] {label}完整路径: {audio_path}")
    #
    #     if not os.path.exists(audio_path):
    #         logger.warning(f"[MimoTTS] {label}文件不存在: {audio_path}")
    #         return None
    #
    #     try:
    #         with open(audio_path, "rb") as f:
    #             audio_bytes = f.read()
    #         audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    #         logger.info(f"[MimoTTS] {label}已加载并编码，大小: {len(audio_base64)} bytes")
    #         return {
    #             "path": audio_path,
    #             "base64": audio_base64,
    #             "mime_type": self._get_mime_type(audio_path),
    #             "label": label,
    #         }
    #     except Exception as e:
    #         logger.error(f"[MimoTTS] 读取{label}失败: {e}")
    #         return None
    #
    # def _setup_reference_audio(self):
    #     self.default_reference_audio = self._load_reference_audio(
    #         self.config.get("reference_audio", []),
    #         "默认参考音频",
    #     )
    #     if self.default_reference_audio:
    #         self.reference_audio_path = self.default_reference_audio["path"]
    #         self.reference_audio_base64 = self.default_reference_audio["base64"]
    #
    # def _setup_bot_reference_audio_files(self):
    #     file_config = self.config.get("bot_reference_audio_files", [])
    #     for relative_path in self._get_uploaded_files(file_config):
    #         audio_info = self._load_reference_audio(relative_path, f"机器人参考声音文件 {relative_path}", False)
    #         if not audio_info:
    #             continue
    #         filename = os.path.basename(relative_path).strip()
    #         self.bot_reference_audio_files[relative_path] = audio_info
    #         self.bot_reference_audio_files[filename] = audio_info
    #         stem, _ = os.path.splitext(filename)
    #         if stem:
    #             self.bot_reference_audio_files.setdefault(stem, audio_info)
    #
    #     if self.bot_reference_audio_files:
    #         unique_files = {info["path"] for info in self.bot_reference_audio_files.values()}
    #         logger.info(f"[MimoTTS] 已加载 {len(unique_files)} 个机器人专属参考声音文件")
    #
    # def _setup_bot_reference_audios(self):
    #     bot_reference_audios = self.config.get("bot_reference_audios", [])
    #     if not bot_reference_audios:
    #         return
    #     if not isinstance(bot_reference_audios, list):
    #         logger.warning("[MimoTTS] 机器人专属参考音频配置不是列表，已忽略")
    #         return
    #
    #     for index, item in enumerate(bot_reference_audios, start=1):
    #         if not isinstance(item, dict):
    #             logger.warning(f"[MimoTTS] 第 {index} 个机器人参考音频配置格式错误，已忽略")
    #             continue
    #
    #         bot_id = str(item.get("bot_id", "")).strip()
    #         if not bot_id:
    #             logger.warning(f"[MimoTTS] 第 {index} 个机器人参考音频未填写机器人 ID，已忽略")
    #             continue
    #
    #         audio_key = str(item.get("reference_audio_filename", "")).strip().replace("\\", "/")
    #         audio_info = self.bot_reference_audio_files.get(audio_key)
    #         if not audio_info and not audio_key:
    #             audio_info = self.bot_reference_audio_files.get(bot_id)
    #         if not audio_info and audio_key:
    #             audio_info = self._load_reference_audio(audio_key, f"机器人 {bot_id} 参考音频", False)
    #         if not audio_info:
    #             logger.warning(f"[MimoTTS] 机器人 {bot_id} 未绑定有效参考音频，将回落默认参考音频")
    #             continue
    #
    #         if bot_id in self.bot_reference_audios:
    #             logger.warning(f"[MimoTTS] 机器人 {bot_id} 的参考音频配置重复，将使用最后一项")
    #         self.bot_reference_audios[bot_id] = audio_info
    #
    #     if self.bot_reference_audios:
    #         logger.info(f"[MimoTTS] 已加载 {len(self.bot_reference_audios)} 个机器人专属参考音频")

    async def initialize(self):
        logger.info("[MimoTTS] 插件初始化中...")
        logger.info(f"[MimoTTS] API Key 配置: {'已配置' if self.api_key else '未配置'}")
        logger.info(f"[MimoTTS] 默认参考音频: {'已上传' if self.reference_audio_base64 else '未上传'}")
        logger.info(f"[MimoTTS] 机器人专属参考音频映射数量: {len(self.bot_reference_audios)}")
        logger.info(f"[MimoTTS] 触发概率: {self.trigger_probability}")
        logger.info(f"[MimoTTS] Base URL: {self.base_url}")
        logger.info(f"[MimoTTS] 模型名称: {self.model_name}")
        if not self.api_key:
            logger.warning("[MimoTTS] 未配置 API Key，声音克隆功能将不可用")

    def _should_trigger_tts(self, reference_audio: dict | None) -> bool:
        if not self.api_key:
            logger.debug("[MimoTTS] 未配置 API Key，跳过 TTS")
            return False
        if not reference_audio or not reference_audio.get("base64"):
            logger.debug("[MimoTTS] 未找到可用参考音频，跳过 TTS")
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

    def _get_mime_type(self, audio_path: str | None) -> str:
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
        }
        if audio_path:
            ext = os.path.splitext(audio_path)[1].lower()
            return mime_types.get(ext, "audio/mpeg")
        return "audio/mpeg"

    def _get_event_platform_name(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_platform_name()).strip().lower()
        except Exception:
            platform_meta = getattr(event, "platform_meta", None)
            return str(getattr(platform_meta, "name", "")).strip().lower()

    def _get_event_bot_id(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_self_id()).strip()
        except Exception:
            message_obj = getattr(event, "message_obj", None)
            return str(getattr(message_obj, "self_id", "")).strip()

    def _is_usable_record_ref(self, ref: str | None) -> bool:
        if not ref:
            return False
        ref = str(ref).strip()
        if not ref:
            return False
        if ref.startswith(("http://", "https://", "base64://")):
            return True
        if ref.startswith("file:///"):
            return os.path.exists(ref[8:])
        return os.path.exists(ref)

    def _normalize_record_file_ref(self, record: Record) -> bool:
        for attr in ("file", "url", "path"):
            ref = getattr(record, attr, None)
            if self._is_usable_record_ref(ref):
                record.file = str(ref).strip()
                return True
        return False

    def _sanitize_record_chain(self, chain: list, quoted: bool = False) -> int:
        replaced_count = 0
        sanitized_chain = []

        for component in chain:
            if isinstance(component, Record):
                if self._normalize_record_file_ref(component):
                    sanitized_chain.append(component)
                else:
                    replaced_count += 1
                    sanitized_chain.append(Plain("[引用语音消息]" if quoted else "[语音消息]"))
                continue

            if isinstance(component, Reply):
                replaced_count += self._sanitize_reply_records(component)

            sanitized_chain.append(component)

        if replaced_count:
            chain[:] = sanitized_chain
        return replaced_count

    def _sanitize_reply_records(self, reply: Reply) -> int:
        replaced_count = 0
        for attr in ("chain", "message", "origin", "content"):
            payload = getattr(reply, attr, None)
            if isinstance(payload, list):
                replaced_count += self._sanitize_record_chain(payload, quoted=True)

        if replaced_count and not str(getattr(reply, "message_str", "") or "").strip():
            reply.message_str = "[引用语音消息]"
            reply.text = reply.message_str
        return replaced_count

    @filter.on_waiting_llm_request(priority=100)
    async def sanitize_invalid_record_before_llm(self, event: AstrMessageEvent):
        message_obj = getattr(event, "message_obj", None)
        message_chain = getattr(message_obj, "message", None)
        if not isinstance(message_chain, list):
            return

        replaced_count = self._sanitize_record_chain(message_chain)
        if not replaced_count:
            return

        placeholder = "[语音消息]"
        if not str(getattr(event, "message_str", "") or "").strip():
            event.message_str = placeholder
        if message_obj and not str(getattr(message_obj, "message_str", "") or "").strip():
            message_obj.message_str = placeholder
        logger.info(f"[MimoTTS] 已替换 {replaced_count} 个无法解析的语音消息段，避免 LLM 请求阶段报错")

    def _select_reference_audio(self, event: AstrMessageEvent) -> dict | None:
        if self._get_event_platform_name(event) != "aiocqhttp":
            return self.default_reference_audio

        bot_id = self._get_event_bot_id(event)
        if bot_id and bot_id in self.bot_reference_audios:
            logger.info(f"[MimoTTS] 命中机器人 {bot_id} 的专属参考音频")
            return self.bot_reference_audios[bot_id]

        if bot_id:
            logger.info(f"[MimoTTS] 未找到机器人 {bot_id} 的专属参考音频，使用默认参考音频")
        else:
            logger.info("[MimoTTS] 未获取到机器人 ID，使用默认参考音频")
        return self.default_reference_audio

    async def _call_mimo_tts(self, text: str, reference_audio: dict) -> bytes | None:
        truncated_text = self._truncate_text(text)
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        # logger.info(f"[MimoTTS] ====== 开始调用 TTS API ======")
        # logger.info(f"[MimoTTS] API URL: {url}")
        # logger.info(f"[MimoTTS] 模型: {self.model_name}")
        # logger.info(f"[MimoTTS] 文本内容: {truncated_text[:100]}...")
        logger.info(
            f"[MimoTTS] 开始调用 TTS API，API URL: {url}，模型: {self.model_name}，"
            f"参考音频: {reference_audio.get('label', '未知')}"
        )

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        voice_value = f"data:{reference_audio.get('mime_type', 'audio/mpeg')};base64,{reference_audio['base64']}"

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

        reference_audio = self._select_reference_audio(event)

        if not self._should_trigger_tts(reference_audio):
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

        audio_data = await self._call_mimo_tts(text_content, reference_audio)

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
