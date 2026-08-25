"""High-capacity MTProto client for sending files up to 2000 MB (2 GB)."""

import logging
from pathlib import Path
from typing import List, Optional, Union
from pyrogram import Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from x2t.bot.config import bot_config
from x2t.models import MediaType, PostMediaResult

logger = logging.getLogger("x2t.mtproto")


class MTProtoClient:
    """Manages raw MTProto connection via Pyrogram for 2GB file transfers."""

    def __init__(self):
        self.app: Optional[Client] = None
        self._is_started = False

    async def start(self):
        """Initialize and start Pyrogram MTProto client."""
        if not bot_config.has_mtproto or self._is_started:
            return

        logger.info("Initializing MTProto Pyrogram client (2GB upload mode enabled)...")
        self.app = Client(
            name="x2t_mtproto_uploader",
            api_id=bot_config.api_id,
            api_hash=bot_config.api_hash,
            bot_token=bot_config.bot_token,
            in_memory=True,
            max_concurrent_transmissions=4,
        )
        await self.app.start()
        self._is_started = True
        logger.info("MTProto Pyrogram client successfully started.")

    async def stop(self):
        """Stop Pyrogram MTProto client."""
        if self.app and self._is_started:
            await self.app.stop()
            self._is_started = False

    def is_ready(self) -> bool:
        return self._is_started and self.app is not None

    def _convert_reply_markup(self, url: str) -> InlineKeyboardMarkup:
        """Create Pyrogram inline keyboard."""
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 مشاهده پست در X", url=url)]]
        )

    async def send_post_media_mtproto(
        self,
        chat_id: Union[int, str],
        result: PostMediaResult,
        caption: str,
        reply_to_message_id: Optional[int] = None,
    ) -> List[Message]:
        """Send all post media via MTProto with support for files up to 2000 MB."""
        if not self.is_ready() or not result.items:
            return []

        markup = self._convert_reply_markup(result.canonical_url)
        sent_msgs: List[Message] = []

        # Case 1: Single Item
        if len(result.items) == 1:
            item = result.items[0]
            local_path = item.local_path

            if item.type == MediaType.GIF or item.is_gif:
                msg = await self.app.send_animation(
                    chat_id=chat_id,
                    animation=local_path,
                    caption=caption,
                    reply_markup=markup,
                    reply_to_message_id=reply_to_message_id,
                )
                sent_msgs.append(msg)
            elif item.type == MediaType.VIDEO:
                msg = await self.app.send_video(
                    chat_id=chat_id,
                    video=local_path,
                    caption=caption,
                    width=item.width or 0,
                    height=item.height or 0,
                    duration=int(item.duration_seconds or 0),
                    supports_streaming=True,
                    reply_markup=markup,
                    reply_to_message_id=reply_to_message_id,
                )
                sent_msgs.append(msg)
            else:  # Photo
                msg = await self.app.send_photo(
                    chat_id=chat_id,
                    photo=local_path,
                    caption=caption,
                    reply_markup=markup,
                    reply_to_message_id=reply_to_message_id,
                )
                sent_msgs.append(msg)

        # Case 2: Multi-Media Group (2 to 4 items)
        else:
            media_group = []
            for idx, item in enumerate(result.items):
                item_caption = caption if idx == 0 else ""
                if item.type == MediaType.PHOTO:
                    media_group.append(
                        InputMediaPhoto(
                            media=item.local_path,
                            caption=item_caption,
                        )
                    )
                else:  # Video or GIF
                    media_group.append(
                        InputMediaVideo(
                            media=item.local_path,
                            caption=item_caption,
                            width=item.width or 0,
                            height=item.height or 0,
                            duration=int(item.duration_seconds or 0),
                            supports_streaming=True,
                        )
                    )

            msgs = await self.app.send_media_group(
                chat_id=chat_id,
                media=media_group,
                reply_to_message_id=reply_to_message_id,
            )
            sent_msgs.extend(msgs)

            # Send inline link button
            btn_msg = await self.app.send_message(
                chat_id=chat_id,
                text="🔗 <i>اطلاعات و لینک پست در توییتر:</i>",
                reply_markup=markup,
            )
            sent_msgs.append(btn_msg)

        return sent_msgs


mtproto_client = MTProtoClient()
