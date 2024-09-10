from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from moviepy.editor import VideoFileClip
import os
from colorama import Fore, Back, Style

load_dotenv()
allowed_usernames = os.getenv('ALLOWED_USERNAMES').split(',')
channel_id = int(os.environ.get('CHANNEL_ID'))
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone_number = os.getenv("PHONE_NUMBER")
edit_message_status = {}
client = TelegramClient('anon', api_id, api_hash)


def get_video_metadata(video_path):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        width, height = clip.size

        print(Fore.WHITE + "===== VIDEO INFORMATION =====")

        print(f"Duration: {duration} seconds")
        print(f"Resolution: {width}x{height}")
        print(Fore.WHITE + "================================")
        return {
            "duration": duration,
            "width": width,
            "height": height
        }
    except Exception as e:
        print(f"Error: {e}")


async def upload_progress(current: int, total: int, message, event):
    caption = message.message
    substring = caption.index('=== === ===')
    caption = caption[:substring]
    percent = current * 100 / total
    print(percent)

    last_percent = edit_message_status[event.message.id]["upload"]
    if (int(percent) != 0 and last_percent != int(percent) and int(
            percent) % 15 == 0) or last_percent == 0 or percent == 100:
        edit_message_status[event.message.id] = {
            "download": None,
            "upload": int(percent) if int(percent) != 0 else 1
        }
        await client.edit_message(
            channel_id,
            message,
            caption + f"=== === ===\nUploading {percent:.2f}%",
        )


async def download_progress(current, total, message, event):
    global edit_message_status
    caption = message.message
    substring = caption.index('=== === ===')
    caption = caption[:substring]
    percent = current * 100 / total
    print(percent)

    last_percent = edit_message_status[event.message.id]["download"]
    if (int(percent) != 0 and last_percent != int(percent) and int(
            percent) % 15 == 0) or last_percent == 0 or percent == 100:
        edit_message_status[event.message.id] = {
            "download": int(percent) if int(percent) != 0 else 1,
            "upload": None
        }
        await client.edit_message(
            channel_id,
            message,
            caption + f"=== === ===\nDownloading {percent:.2f}%",
        )


print(Fore.GREEN + "CODE IS RUNNING...")

with client:
    @client.on(events.NewMessage(from_users=allowed_usernames))
    async def handler(event):
        global edit_message_status
        print(Fore.RED + "New message detected...")
        if event.message.file:
            if event.message.file.mime_type.startswith('video'):
                print(Fore.BLUE + "Downloading Thumbnail...")
                thumbnail_path = await client.download_media(event.message, thumb=-1)
                print(Fore.BLUE + "Thumbnail Downloading finished.")

                print(event.message.file.name)

                # status :
                status_message = await client.send_message(
                    channel_id,
                    event.message.message + "\n=== === ===" + "\nDownloading...",
                )

                # print(str(event.message.date))
                edit_message_status[event.message.id] = {
                    "download": 0,
                    "upload": None
                }

                print(edit_message_status)

                print(Fore.CYAN + "Downloading Video...")
                file_path = await event.message.download_media(
                    progress_callback=lambda current, total: download_progress(current, total, status_message, event)
                )
                print(Fore.CYAN + "Video Downloading finished.")
                if file_path:
                    video_data = get_video_metadata(file_path)
                    print(Fore.YELLOW + "Sending to channel...")
                    await client.send_file(
                        channel_id,
                        file_path,
                        thumb=thumbnail_path,
                        supports_streaming=True,
                        caption=event.message.message,
                        attributes=[
                            DocumentAttributeVideo(
                                duration=video_data['duration'],
                                w=video_data["width"],
                                h=video_data["height"],
                                supports_streaming=True
                            )
                        ],
                        progress_callback=lambda current, total: upload_progress(current, total, status_message, event)
                    )
                    print(Fore.YELLOW + "Video sent to channel.")
                    await client.delete_messages(channel_id, status_message.id)

                    print(Fore.CYAN + 'Removing files...')
                    os.remove(thumbnail_path)
                    os.remove(file_path)
                    print(Fore.CYAN + "Files removed.")

                    del edit_message_status[event.message.id]

                else:
                    print(Fore.RED + "File download failed.")
            else:
                print(Fore.RED + "There is no video")
        else:
            print(Fore.RED + "There is no video")


    client.loop.run_forever()
