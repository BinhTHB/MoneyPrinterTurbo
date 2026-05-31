import glob
import itertools
import io
import os
import random
import gc
import shutil
import subprocess
import unicodedata
import re
from contextlib import redirect_stdout
from typing import List
from loguru import logger
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    afx,
)
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import Image, ImageFont

from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services.utils import video_effects
from app.utils import file_security, utils

class SubClippedVideoClip:
    def __init__(self, file_path, start_time=None, end_time=None, width=None, height=None, duration=None):
        self.file_path = file_path
        self.start_time = start_time
        self.end_time = end_time
        self.width = width
        self.height = height
        if duration is None:
            self.duration = end_time - start_time
        else:
            self.duration = duration

    def __str__(self):
        return f"SubClippedVideoClip(file_path={self.file_path}, start_time={self.start_time}, end_time={self.end_time}, duration={self.duration}, width={self.width}, height={self.height})"


audio_codec = "aac"
# Docker é‡Œçš„ ffmpeg/AAC ç»„åˆåœ¨é»˜è®¤é…ç½®ä¸‹æ›´å®¹æ˜“å‡ºçŽ°éŸ³é¢‘è´¨é‡æ³¢åŠ¨ï¼Œ
# è¿™é‡Œæ˜¾å¼æŠ¬é«˜éŸ³é¢‘ç çŽ‡ï¼Œé¿å…æˆç‰‡é˜¶æ®µå› ä¸ºé»˜è®¤å€¼è¿‡ä½Žè€Œå¼•å…¥æ˜Žæ˜¾å¤±çœŸã€‚
audio_bitrate = "192k"
video_codec = "libx264"
fps = 30
_BGM_EXTENSIONS = (".mp3",)


def get_ffmpeg_binary():
    # ä¼˜å…ˆå¤ç”¨ç”¨æˆ·åœ¨ config.toml / çŽ¯å¢ƒå˜é‡é‡Œæ˜¾å¼æŒ‡å®šçš„ ffmpegï¼Œå¯é¿å…
    # Windows ä¾¿æºåŒ…ã€Dockerã€è‡ªå®šä¹‰å®‰è£…ç›®å½•ç­‰åœºæ™¯ä¸‹ PATH ä¸ä¸€è‡´ã€‚
    configured_ffmpeg = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if configured_ffmpeg:
        return configured_ffmpeg

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled_ffmpeg:
            return bundled_ffmpeg
    except Exception as exc:
        logger.warning(f"failed to resolve bundled ffmpeg binary: {str(exc)}")

    return "ffmpeg"


def _escape_ffmpeg_concat_path(file_path: str) -> str:
    # concat demuxer ä½¿ç”¨å•å¼•å·åŒ…è£¹è·¯å¾„ï¼Œè·¯å¾„ä¸­çš„å•å¼•å·éœ€è¦å…ˆè½¬ä¹‰ã€‚
    return file_path.replace("'", "'\\''")


def concat_video_clips_with_ffmpeg(
    clip_files: List[str], output_file: str, threads: int, output_dir: str
):
    concat_list_file = os.path.join(output_dir, "ffmpeg-concat-list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as fp:
        for clip_file in clip_files:
            absolute_path = os.path.abspath(clip_file)
            fp.write(f"file '{_escape_ffmpeg_concat_path(absolute_path)}'\n")

    command = [
        get_ffmpeg_binary(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_file,
        "-c:v",
        video_codec,
        "-threads",
        str(threads or 2),
        "-pix_fmt",
        "yuv420p",
        output_file,
    ]

    try:
        # ä½¿ç”¨ ffmpeg åªåšä¸€æ¬¡ä¸²è”ä¸Žç¼–ç ï¼Œé¿å… MoviePy é€æ®µåˆå¹¶æ—¶åå¤é‡ç¼–ç ï¼Œ
        # ä»Žè€Œé™ä½Žç”»è´¨åŠ£åŒ–ä¸Žé¢œè‰²åç§»é£Žé™©ã€‚
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            error_message = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(error_message or "ffmpeg concat failed")
    finally:
        delete_files(concat_list_file)


def _sanitize_image_file(image_path: str) -> str:
    # æŸäº›æœ¬åœ°å›¾ç‰‡è™½ç„¶èƒ½è¢« Pillow æ‰“å¼€ï¼Œä½†ä¼šå› ä¸ºæŸåçš„ EXIF/eXIf å…ƒæ•°æ®å¯¼è‡´
    # ImageClip åœ¨è§£æžé˜¶æ®µç›´æŽ¥æŠ›å¼‚å¸¸ã€‚è¿™é‡Œé‡æ–°å¯¼å‡ºä¸€ä»½â€œå¹²å‡€å›¾ç‰‡â€ï¼ŒæŠŠåå…ƒæ•°æ®å‰¥ç¦»æŽ‰ã€‚
    image_root, _ = os.path.splitext(image_path)
    sanitized_path = f"{image_root}.sanitized.png"

    with Image.open(image_path) as image:
        image.load()
        # ç»Ÿä¸€å¯¼å‡ºä¸º PNGï¼Œé¿å… JPEG/PNG ä¸åŒå…ƒæ•°æ®è·¯å¾„ç»§ç»­æŠŠåå—å¸¦è¿‡åŽ»ã€‚
        cleaned_image = Image.new(image.mode, image.size)
        cleaned_image.putdata(list(image.getdata()))
        cleaned_image.save(sanitized_path)

    return sanitized_path


def _open_image_clip_with_fallback(image_path: str):
    # ä¼˜å…ˆç›´æŽ¥æ‰“å¼€åŽŸå§‹å›¾ç‰‡ï¼›å¦‚æžœå› ä¸ºæŸåå…ƒæ•°æ®å¤±è´¥ï¼Œå†å°è¯•ç”Ÿæˆæ— å…ƒæ•°æ®å‰¯æœ¬ã€‚
    try:
        return ImageClip(image_path), image_path
    except Exception as exc:
        logger.warning(
            f"failed to open image directly, trying sanitized copy: {image_path}, error: {str(exc)}"
        )
        sanitized_path = _sanitize_image_file(image_path)
        return ImageClip(sanitized_path), sanitized_path


def _open_video_clip_quietly(video_path: str, audio: bool = False) -> VideoFileClip:
    """
    å®‰é™åœ°æ‰“å¼€è§†é¢‘æ–‡ä»¶ï¼Œé¿å… MoviePy 2.1.x æŠŠ ffmpeg æŽ¢æµ‹ä¿¡æ¯ç›´æŽ¥æ‰“å°åˆ° stdoutã€‚

    èƒŒæ™¯ï¼š
    å½“å‰ä¾èµ–ç‰ˆæœ¬çš„ `FFMPEG_VideoReader` å†…éƒ¨å­˜åœ¨ `print(self.infos)` å’Œ
    `print(ffmpeg command)`ï¼Œè¯»å–æ— éŸ³è½¨çš„ä¸­é—´è§†é¢‘æ—¶ä¼šè¾“å‡º
    `audio_found: False`ã€‚è¿™åªæ˜¯è¾“å…¥ç´ æ metadataï¼Œä¸ä»£è¡¨æœ€ç»ˆæˆç‰‡æ²¡æœ‰éŸ³é¢‘ï¼Œ
    ä½†ä¼šè¯¯å¯¼ WebUI/ç»ˆç«¯ç”¨æˆ·ä»¥ä¸ºç”Ÿæˆå¤±è´¥ã€‚

    å®žçŽ°ï¼š
    1. åªåœ¨æ‰“å¼€ VideoFileClip çš„çŸ­çª—å£å†…é‡å®šå‘ stdoutï¼›
    2. é»˜è®¤ `audio=False`ï¼Œå› ä¸ºé¡¹ç›®è§†é¢‘ç´ æé˜¶æ®µä¸éœ€è¦ä¿ç•™ç´ æåŽŸå£°ï¼Œ
       æœ€ç»ˆéŸ³é¢‘ä¼šåœ¨ `generate_video()` é˜¶æ®µç»Ÿä¸€æŒ‚è½½ï¼›
    3. å¦‚æžœä¾èµ–åº“ç¡®å®žè¾“å‡ºäº†å†…å®¹ï¼Œé™çº§ä¸º debug æ—¥å¿—ï¼Œä¾¿äºŽå¿…è¦æ—¶æŽ’æŸ¥ã€‚
    """
    captured_stdout = io.StringIO()
    with redirect_stdout(captured_stdout):
        clip = VideoFileClip(video_path, audio=audio)

    moviepy_stdout = captured_stdout.getvalue().strip()
    if moviepy_stdout:
        logger.debug(
            "suppressed MoviePy video reader stdout for "
            f"{video_path}, chars: {len(moviepy_stdout)}"
        )

    return clip


def close_clip(clip):
    if clip is None:
        return
        
    try:
        # close main resources
        if hasattr(clip, 'reader') and clip.reader is not None:
            clip.reader.close()
            
        # close audio resources
        if hasattr(clip, 'audio') and clip.audio is not None:
            if hasattr(clip.audio, 'reader') and clip.audio.reader is not None:
                clip.audio.reader.close()
            del clip.audio
            
        # close mask resources
        if hasattr(clip, 'mask') and clip.mask is not None:
            if hasattr(clip.mask, 'reader') and clip.mask.reader is not None:
                clip.mask.reader.close()
            del clip.mask
            
        # handle child clips in composite clips
        if hasattr(clip, 'clips') and clip.clips:
            for child_clip in clip.clips:
                if child_clip is not clip:  # avoid possible circular references
                    close_clip(child_clip)
            
        # clear clip list
        if hasattr(clip, 'clips'):
            clip.clips = []
            
    except Exception as e:
        logger.error(f"failed to close clip: {str(e)}")
    
    del clip
    gc.collect()

def delete_files(files: List[str] | str):
    if isinstance(files, str):
        files = [files]

    for file in files:
        try:
            os.remove(file)
        except Exception as e:
            logger.debug(f"failed to delete file {file}: {str(e)}")


def _resolve_bgm_file_path(song_dir: str, bgm_file: str) -> str:
    # èƒŒæ™¯éŸ³ä¹åªå…è®¸è¯»å– resource/songs ç›®å½•å†…çš„æ–‡ä»¶ï¼Œé¿å…ç”¨æˆ·è¾“å…¥ä»»æ„è·¯å¾„åŽ
    # è¢« MoviePy æ‰“å¼€ã€‚è¿™é‡Œå…¼å®¹ä¸¤ç§å¸¸è§è¾“å…¥ï¼š
    # 1. output000.mp3ï¼šæ¥è‡ª BGM åˆ—è¡¨æˆ–ç”¨æˆ·åªå¡«å†™æ–‡ä»¶å
    # 2. ./resource/songs/output000.mp3ï¼šç”¨æˆ·æŒ‰é¡¹ç›®ç›®å½•ç»“æž„å¡«å†™çš„ç›¸å¯¹è·¯å¾„
    # ä¸¤ç§å†™æ³•æœ€ç»ˆéƒ½ä¼šå†æ¬¡é€šè¿‡ resource/songs ç™½åå•æ ¡éªŒï¼Œä¸èƒ½ç»•è¿‡ç›®å½•é™åˆ¶ã€‚
    try:
        return file_security.resolve_path_within_directory(song_dir, bgm_file)
    except ValueError as song_dir_exc:
        if os.path.isabs(bgm_file):
            raise song_dir_exc

        project_relative_file = os.path.join(utils.root_dir(), bgm_file)
        try:
            return file_security.resolve_path_within_directory(
                song_dir, project_relative_file
            )
        except ValueError as root_dir_exc:
            raise ValueError(str(root_dir_exc)) from song_dir_exc


def get_bgm_file(bgm_type: str = "random", bgm_file: str = ""):
    if not bgm_type:
        return ""

    if bgm_file:
        song_dir = utils.song_dir()
        try:
            resolved_bgm_file = _resolve_bgm_file_path(song_dir, bgm_file)
        except ValueError as exc:
            # API è¯·æ±‚é‡Œçš„ bgm_file æ¥è‡ªç”¨æˆ·è¾“å…¥ï¼Œä¸èƒ½ç›´æŽ¥æŠŠä»»æ„ç»å¯¹è·¯å¾„äº¤ç»™
            # MoviePy æ‰“å¼€ã€‚è¿™é‡Œå¼ºåˆ¶é™åˆ¶åˆ° resource/songs ç›®å½•ï¼Œé˜»æ­¢è¯»å–
            # /etc/passwdã€é…ç½®æ–‡ä»¶ã€å¯†é’¥ç­‰éžèƒŒæ™¯éŸ³ä¹æ–‡ä»¶ã€‚
            logger.warning(
                f"reject unsafe bgm file: {bgm_file}, song_dir: {song_dir}, error: {str(exc)}"
            )
            return ""

        if not resolved_bgm_file.lower().endswith(_BGM_EXTENSIONS):
            logger.warning(f"reject unsupported bgm file extension: {resolved_bgm_file}")
            return ""

        return resolved_bgm_file

    if bgm_type == "random":
        suffix = "*.mp3"
        song_dir = utils.song_dir()
        files = glob.glob(os.path.join(song_dir, suffix))
        # å½“èƒŒæ™¯éŸ³ä¹ç›®å½•ä¸ºç©ºæ—¶ï¼Œç›´æŽ¥å›žé€€ä¸ºâ€œä¸ä½¿ç”¨ BGMâ€ï¼Œé¿å… random.choice([]) æŠ›å¼‚å¸¸ã€‚
        if not files:
            logger.warning(f"no bgm files found in song directory: {song_dir}")
            return ""
        return random.choice(files)

    return ""


def combine_videos(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    video_transition_mode: VideoTransitionMode = None,
    max_clip_duration: int = 5,
    threads: int = 2,
) -> str:
    audio_clip = AudioFileClip(audio_file)
    try:
        # è¿™é‡Œåªéœ€è¦è¯»å–æ—ç™½éŸ³é¢‘æ—¶é•¿æ¥å†³å®šç´ æè§†é¢‘æ‹¼æŽ¥é•¿åº¦ï¼›åŽç»­ä¸ä¼šå†ä½¿ç”¨
        # audio_clipã€‚è¯»å–å®ŒæˆåŽç«‹å³å…³é—­ï¼Œé¿å…æ—©é€€æˆ–å¼‚å¸¸è·¯å¾„æ³„æ¼æ–‡ä»¶å¥æŸ„ã€‚
        audio_duration = audio_clip.duration
    finally:
        close_clip(audio_clip)
    logger.info(f"audio duration: {audio_duration} seconds")
    logger.info(f"maximum clip duration: {max_clip_duration} seconds")

    # å…¼å®¹ API ç›´æŽ¥è°ƒç”¨æ—¶æœªä¼ è½¬åœºæ¨¡å¼çš„æƒ…å†µï¼Œé¿å…åŽç»­è®¿é—® .value æ—¶å´©æºƒã€‚
    transition_value = getattr(video_transition_mode, "value", video_transition_mode)
    output_dir = os.path.dirname(combined_video_path)

    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()

    processed_clips = []
    subclipped_items = []
    video_duration = 0
    for video_path in video_paths:
        clip = _open_video_clip_quietly(video_path)
        clip_duration = clip.duration
        clip_w, clip_h = clip.size
        close_clip(clip)
        
        start_time = 0

        while start_time < clip_duration:
            end_time = min(start_time + max_clip_duration, clip_duration)

            # ä¿ç•™æ‰€æœ‰æœ‰æ•ˆåˆ†æ®µã€‚
            # è¿™æ ·æ—¢ä¸ä¼šä¸¢æŽ‰â€œæ•´æ®µè§†é¢‘æœ¬èº«å°±çŸ­äºŽ max_clip_durationâ€çš„ç´ æï¼Œ
            # ä¹Ÿä¸ä¼šåžæŽ‰é•¿è§†é¢‘æœ€åŽå‰©ä¸‹çš„ä¸€å°æ®µå°¾éƒ¨å†…å®¹ã€‚
            if end_time > start_time:
                subclipped_items.append(
                    SubClippedVideoClip(
                        file_path=video_path,
                        start_time=start_time,
                        end_time=end_time,
                        width=clip_w,
                        height=clip_h,
                    )
                )

            start_time = end_time
            if video_concat_mode.value == VideoConcatMode.sequential.value:
                break

    # random subclipped_items order
    if video_concat_mode.value == VideoConcatMode.random.value:
        random.shuffle(subclipped_items)
        
    logger.debug(f"total subclipped items: {len(subclipped_items)}")
    
    # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
    for i, subclipped_item in enumerate(subclipped_items):
        if video_duration > audio_duration:
            break
        
        logger.debug(f"processing clip {i+1}: {subclipped_item.width}x{subclipped_item.height}, current duration: {video_duration:.2f}s, remaining: {audio_duration - video_duration:.2f}s")
        
        try:
            clip = _open_video_clip_quietly(subclipped_item.file_path).subclipped(
                subclipped_item.start_time, subclipped_item.end_time
            )
            clip_duration = clip.duration
            # Not all videos are same size, so we need to resize them
            clip_w, clip_h = clip.size
            if clip_w != video_width or clip_h != video_height:
                clip_ratio = clip.w / clip.h
                video_ratio = video_width / video_height
                logger.debug(f"resizing clip, source: {clip_w}x{clip_h}, ratio: {clip_ratio:.2f}, target: {video_width}x{video_height}, ratio: {video_ratio:.2f}")
                
                if clip_ratio == video_ratio:
                    clip = clip.resized(new_size=(video_width, video_height))
                else:
                    if clip_ratio > video_ratio:
                        scale_factor = video_width / clip_w
                    else:
                        scale_factor = video_height / clip_h

                    new_width = int(clip_w * scale_factor)
                    new_height = int(clip_h * scale_factor)

                    background = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(clip_duration)
                    clip_resized = clip.resized(new_size=(new_width, new_height)).with_position("center")
                    clip = CompositeVideoClip([background, clip_resized])
                    
            shuffle_side = random.choice(["left", "right", "top", "bottom"])
            if transition_value in (None, VideoTransitionMode.none.value):
                clip = clip
            elif transition_value == VideoTransitionMode.fade_in.value:
                clip = video_effects.fadein_transition(clip, 1)
            elif transition_value == VideoTransitionMode.fade_out.value:
                clip = video_effects.fadeout_transition(clip, 1)
            elif transition_value == VideoTransitionMode.slide_in.value:
                clip = video_effects.slidein_transition(clip, 1, shuffle_side)
            elif transition_value == VideoTransitionMode.slide_out.value:
                clip = video_effects.slideout_transition(clip, 1, shuffle_side)
            elif transition_value == VideoTransitionMode.shuffle.value:
                transition_funcs = [
                    lambda c: video_effects.fadein_transition(c, 1),
                    lambda c: video_effects.fadeout_transition(c, 1),
                    lambda c: video_effects.slidein_transition(c, 1, shuffle_side),
                    lambda c: video_effects.slideout_transition(c, 1, shuffle_side),
                ]
                shuffle_transition = random.choice(transition_funcs)
                clip = shuffle_transition(clip)

            if clip.duration > max_clip_duration:
                clip = clip.subclipped(0, max_clip_duration)
                
            # wirte clip to temp file
            clip_file = f"{output_dir}/temp-clip-{i+1}.mp4"
            clip.write_videofile(clip_file, logger=None, fps=fps, codec=video_codec)

            # Store clip duration before closing
            clip_duration_saved = clip.duration
            close_clip(clip)

            processed_clips.append(SubClippedVideoClip(file_path=clip_file, duration=clip_duration_saved, width=clip_w, height=clip_h))
            video_duration += clip_duration_saved
            
        except Exception as e:
            logger.error(f"failed to process clip: {str(e)}")
    
    # loop processed clips until the video duration matches or exceeds the audio duration.
    if video_duration < audio_duration:
        logger.warning(f"video duration ({video_duration:.2f}s) is shorter than audio duration ({audio_duration:.2f}s), looping clips to match audio length.")
        base_clips = processed_clips.copy()
        for clip in itertools.cycle(base_clips):
            if video_duration >= audio_duration:
                break
            processed_clips.append(clip)
            video_duration += clip.duration
        logger.info(f"video duration: {video_duration:.2f}s, audio duration: {audio_duration:.2f}s, looped {len(processed_clips)-len(base_clips)} clips")
     
    # merge video clips progressively, avoid loading all videos at once to avoid memory overflow
    logger.info("starting clip merging process")
    if not processed_clips:
        logger.warning("no clips available for merging")
        return combined_video_path
    
    # if there is only one clip, use it directly
    if len(processed_clips) == 1:
        logger.info("using single clip directly")
        shutil.copy(processed_clips[0].file_path, combined_video_path)
        delete_files([processed_clips[0].file_path])
        logger.info("video combining completed")
        return combined_video_path

    clip_files = [clip.file_path for clip in processed_clips]
    logger.info(f"concatenating {len(clip_files)} clips with ffmpeg")
    concat_video_clips_with_ffmpeg(
        clip_files=clip_files,
        output_file=combined_video_path,
        threads=threads,
        output_dir=output_dir,
    )
    
    # clean temp files
    delete_files(clip_files)
            
    logger.info("video combining completed")
    return combined_video_path


def wrap_text(text, max_width, font="Arial", fontsize=60):
    # å­—å¹•æ¢è¡Œå¿…é¡»åœ¨çœŸæ­£åˆ›å»º TextClip å‰å®Œæˆï¼Œå¦åˆ™ MoviePy åªä¼šæŒ‰åŽŸå§‹æ–‡æœ¬
    # è®¡ç®—æ¸²æŸ“åŒºåŸŸã€‚è¿™é‡Œç”¨ PIL æŒ‰å½“å‰å­—ä½“å’Œå­—å·æµ‹é‡å®½åº¦ï¼Œç¡®ä¿æ¯ä¸€è¡Œéƒ½å°½é‡
    # æŽ§åˆ¶åœ¨è§†é¢‘å¯ç”¨å®½åº¦å†…ï¼Œé¿å…å¤§å­—å·æˆ–ä¸­æ–‡é•¿å¥ç›´æŽ¥æº¢å‡ºç”»é¢ã€‚
    font = ImageFont.truetype(font, fontsize)
    max_width = int(max_width)

    def get_text_size(inner_text):
        inner_text = inner_text.strip()
        if not inner_text:
            return 0, fontsize
        left, top, right, bottom = font.getbbox(inner_text)
        return right - left, bottom - top

    width, height = get_text_size(text)
    if width <= max_width:
        return text, height

    def split_long_token(token):
        # å½“ä¸€ä¸ª token æœ¬èº«å°±è¶…å®½æ—¶ï¼ˆå¸¸è§äºŽä¸­æ–‡æ— ç©ºæ ¼é•¿å¥ï¼Œæˆ–è‹±æ–‡è¶…é•¿å•è¯ï¼‰ï¼Œ
        # é€€åŒ–ä¸ºå­—ç¬¦çº§æ‹†åˆ†ã€‚å…³é”®ç‚¹æ˜¯ï¼šæ£€æµ‹åˆ° candidate è¶…å®½æ—¶ï¼Œå…ˆæäº¤ä¸Šä¸€ä¸ª
        # ä»ç„¶åˆæ³•çš„ currentï¼Œå†æŠŠå½“å‰å­—ç¬¦æ”¾å…¥ä¸‹ä¸€è¡Œï¼Œä¸èƒ½æŠŠè¶…å®½å­—ç¬¦å¡žå›žä¸Šä¸€è¡Œã€‚
        lines = []
        current = ""
        for char in token:
            candidate = f"{current}{char}"
            candidate_width, _ = get_text_size(candidate)
            if candidate_width <= max_width or not current:
                current = candidate
                continue
            lines.append(current)
            current = char
        if current:
            lines.append(current)
        return lines

    lines = []
    current = ""
    words = text.split(" ")
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        candidate_width, _ = get_text_size(candidate)
        if candidate_width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)

        word_width, _ = get_text_size(word)
        if word_width <= max_width:
            current = word
        else:
            lines.extend(split_long_token(word))
            current = ""

    if current:
        lines.append(current)

    result = "\n".join(line.strip() for line in lines if line.strip()).strip()
    height = len(lines) * height
    return result, height


def _detect_vietnamese_in_file(subtitle_path: str) -> bool:
    if not subtitle_path or not os.path.isfile(subtitle_path):
        return False
    try:
        with open(subtitle_path, "r", encoding="utf-8") as f:
            content = f.read()
        vietnamese_chars = re.compile(
            r"[Ã Ã¡áº£Ã£áº¡Äƒáº±áº¯áº³áºµáº·Ã¢áº§áº¥áº©áº«áº­Ã¨Ã©áº»áº½áº¹Ãªá»áº¿á»ƒá»…á»‡Ã¬Ã­á»‰Ä©á»‹Ã²Ã³á»Ãµá»Ã´á»“á»‘á»•á»—á»™Æ¡á»á»›á»Ÿá»¡á»£"
            r"Ã¹Ãºá»§Å©á»¥Æ°á»«á»©á»­á»¯á»±á»³Ã½á»·á»¹á»µÄ‘Ã€Ãáº¢Ãƒáº Ä‚áº°áº®áº²áº´áº¶Ã‚áº¦áº¤áº¨áºªáº¬ÃˆÃ‰áººáº¼áº¸ÃŠá»€áº¾á»‚á»„á»†ÃŒÃá»ˆÄ¨á»Š"
            r"Ã’Ã“á»ŽÃ•á»ŒÃ”á»’á»á»”á»–á»˜Æ á»œá»šá»žá» á»¢Ã™Ãšá»¦Å¨á»¤Æ¯á»ªá»¨á»¬á»®á»°á»²Ãá»¶á»¸á»´Ä]"
        )
        return bool(vietnamese_chars.search(content))
    except Exception:
        return False


def generate_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params: VideoParams,
):
    aspect = VideoAspect(params.video_aspect)
    video_width, video_height = aspect.to_resolution()

    logger.info(f"generating video: {video_width} x {video_height}")
    logger.info(f"  â‘  video: {video_path}")
    logger.info(f"  â‘¡ audio: {audio_path}")
    logger.info(f"  â‘¢ subtitle: {subtitle_path}")
    logger.info(f"  â‘£ output: {output_file}")

    # https://github.com/harry0703/MoneyPrinterTurbo/issues/217
    # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'final-1.mp4.tempTEMP_MPY_wvf_snd.mp3'
    # write into the same directory as the output file
    output_dir = os.path.dirname(output_file)

    font_path = ""
    if params.subtitle_enabled:
        if not params.font_name:
            params.font_name = "STHeitiMedium.ttc"
        font_path = os.path.join(utils.font_dir(), params.font_name)
        if os.name == "nt":
            font_path = font_path.replace("\\", "/")

        if _detect_vietnamese_in_file(subtitle_path):
            viet_font = os.path.join(utils.font_dir(), "UTM Kabel KT.ttf")
            if os.path.exists(viet_font) and "UTM Kabel KT" not in params.font_name:
                logger.info(
                    f"  â‘¥ Vietnamese detected, switching font to UTM Kabel KT.ttf "
                    f"(was: {params.font_name})"
                )
                font_path = viet_font.replace("\\", "/") if os.name == "nt" else viet_font
                params.font_name = "UTM Kabel KT.ttf"

        logger.info(f"  â‘¤ font: {font_path}")

    def resolve_subtitle_background_color():
        # å…¼å®¹åŽ†å²å‚æ•°ï¼šAPI é‡Œ `text_background_color` æ—¢å¯èƒ½æ˜¯å¸ƒå°”å€¼ï¼Œ
        # ä¹Ÿå¯èƒ½æ˜¯å®žé™…é¢œè‰²å­—ç¬¦ä¸²ã€‚ç»Ÿä¸€åœ¨è¿™é‡Œå½’ä¸€åŒ–ï¼Œé¿å…æŠŠ True/False
        # ç›´æŽ¥ä¼ ç»™ TextClip åŽå‡ºçŽ°ä¸å¯é¢„æœŸçš„æ¸²æŸ“ç»“æžœã€‚
        if isinstance(params.text_background_color, bool):
            return "#000000" if params.text_background_color else None
        return params.text_background_color

    def create_text_clip(subtitle_item):
        params.font_size = int(params.font_size)
        params.stroke_width = int(params.stroke_width)
        phrase = subtitle_item[1]
        max_width = video_width * 0.9
        wrapped_txt, txt_height = wrap_text(
            phrase, max_width=max_width, font=font_path, fontsize=params.font_size
        )
        interline = int(params.font_size * 0.25)
        line_count = wrapped_txt.count("\n") + 1
        vertical_padding = int(params.font_size * 0.35)
        # MoviePy åœ¨ `method=label` ä¸‹ä¼šè‡ªåŠ¨æ”¶ç¼©æ–‡æœ¬æ¡†é«˜åº¦ï¼Œé‡åˆ°å¤šè¡Œå­—å¹•ã€
        # æè¾¹æˆ–èƒŒæ™¯è‰²æ—¶ï¼Œå®¹æ˜“æŠŠæœ€åŽä¸€è¡Œçš„ä¸‹åŠéƒ¨åˆ†è£æŽ‰ã€‚è¿™é‡Œæ˜¾å¼ä¼ å…¥
        # ä¸€ä¸ªæ›´ä¿å®ˆçš„é«˜åº¦ï¼ŒæŠŠè¡Œé—´è·å’Œé¢å¤–ä¸Šä¸‹ç•™ç™½ä¸€å¹¶ç®—è¿›åŽ»ï¼Œä¿è¯å­—å¹•
        # èƒŒæ™¯æ¡†ä¸Žæ–‡å­—æœ¬èº«éƒ½èƒ½å®Œæ•´æ¸²æŸ“å‡ºæ¥ã€‚
        size = (
            int(max_width),
            int(txt_height + vertical_padding + (interline * line_count)),
        )

        _clip = TextClip(
            text=wrapped_txt,
            font=font_path,
            font_size=params.font_size,
            color=params.text_fore_color,
            bg_color=resolve_subtitle_background_color(),
            stroke_color=params.stroke_color,
            stroke_width=params.stroke_width,
            interline=interline,
            size=size,
            text_align="center",
        )
        duration = subtitle_item[0][1] - subtitle_item[0][0]
        _clip = _clip.with_start(subtitle_item[0][0])
        _clip = _clip.with_end(subtitle_item[0][1])
        _clip = _clip.with_duration(duration)
        if params.subtitle_position == "bottom":
            _clip = _clip.with_position(("center", video_height * 0.95 - _clip.h))
        elif params.subtitle_position == "top":
            _clip = _clip.with_position(("center", video_height * 0.05))
        elif params.subtitle_position == "custom":
            # Ensure the subtitle is fully within the screen bounds
            margin = 10  # Additional margin, in pixels
            max_y = video_height - _clip.h - margin
            min_y = margin
            custom_y = (video_height - _clip.h) * (params.custom_position / 100)
            custom_y = max(
                min_y, min(custom_y, max_y)
            )  # Constrain the y value within the valid range
            _clip = _clip.with_position(("center", custom_y))
        else:  # center
            _clip = _clip.with_position(("center", "center"))
        return _clip

    video_clip = _open_video_clip_quietly(video_path)
    audio_clip = AudioFileClip(audio_path).with_effects(
        [afx.MultiplyVolume(params.voice_volume)]
    )

    def make_textclip(text):
        return TextClip(
            text=text,
            font=font_path,
            font_size=params.font_size,
        )

    if subtitle_path and os.path.exists(subtitle_path):
        sub = SubtitlesClip(
            subtitles=subtitle_path, encoding="utf-8", make_textclip=make_textclip
        )
        text_clips = []
        for item in sub.subtitles:
            clip = create_text_clip(subtitle_item=item)
            text_clips.append(clip)
        video_clip = CompositeVideoClip([video_clip, *text_clips])

    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)
    if bgm_file:
        try:
            bgm_clip = AudioFileClip(bgm_file).with_effects(
                [
                    afx.MultiplyVolume(params.bgm_volume),
                    afx.AudioFadeOut(3),
                    afx.AudioLoop(duration=video_clip.duration),
                ]
            )
            audio_clip = CompositeAudioClip([audio_clip, bgm_clip])
        except Exception as e:
            logger.error(f"failed to add bgm: {str(e)}")

    video_clip = video_clip.with_audio(audio_clip)
    # æ˜¾å¼æ²¿ç”¨è¾“å…¥éŸ³é¢‘çš„é‡‡æ ·çŽ‡ï¼›å¦‚æžœå–ä¸åˆ°ï¼Œå†å›žé€€åˆ° MoviePy é»˜è®¤çš„ 44100Hzã€‚
    # è¿™æ ·å¯ä»¥å‡å°‘ä¸åŒè¿è¡ŒçŽ¯å¢ƒï¼Œå°¤å…¶æ˜¯ Docker çŽ¯å¢ƒä¸­å†æ¬¡é‡é‡‡æ ·å¸¦æ¥çš„éŸ³è´¨æ³¢åŠ¨ã€‚
    output_audio_fps = int(getattr(audio_clip, "fps", 0) or 44100)
    video_clip.write_videofile(
        output_file,
        audio_codec=audio_codec,
        audio_fps=output_audio_fps,
        audio_bitrate=audio_bitrate,
        temp_audiofile_path=output_dir,
        threads=params.n_threads or 2,
        logger=None,
        fps=fps,
    )
    # Detach audio from video before closing to avoid double-free of
    # FFMPEG_AudioReader on Windows (OSError: [WinError 6] The handle is invalid).
    video_clip = video_clip.with_audio(None)
    try:
        audio_clip.close()
    except Exception as e:
        logger.debug("Suppressed error closing audio clip: " + str(e))
    if bgm_file and "bgm_clip" in dir():
        try:
            bgm_clip.close()
        except Exception as e:
            logger.debug("Suppressed error closing BGM clip: " + str(e))
    video_clip.close()
    del video_clip


def preprocess_video(materials: List[MaterialInfo], clip_duration=4):
    # WebUI åœ¨æŸäº›äºŒæ¬¡ç”Ÿæˆåœºæ™¯ä¸‹å¯èƒ½ä¼ å…¥ç©ºç´ æåˆ—è¡¨ï¼Œè¿™é‡Œç›´æŽ¥è¿”å›žç©ºç»“æžœï¼Œé¿å…æŠ›å‡º NoneType å¼‚å¸¸ã€‚
    if not materials:
        return []

    # ä»…è¿”å›žé€šè¿‡é¢„å¤„ç†æ ¡éªŒçš„ç´ æï¼Œé¿å…ä½Žåˆ†è¾¨çŽ‡å›¾ç‰‡ç»§ç»­è¿›å…¥åŽç»­çš„è§†é¢‘åˆæˆæµç¨‹ã€‚
    valid_materials = []
    local_videos_dir = utils.storage_dir("local_videos", create=True)

    for material in materials:
        if not material.url:
            continue

        try:
            material_source_path = file_security.resolve_path_within_directory(
                local_videos_dir, material.url
            )
        except ValueError as exc:
            # local video_source çš„ç´ æè·¯å¾„æ¥è‡ª API å‚æ•°ï¼Œå¿…é¡»é™åˆ¶åœ¨ä¸“ç”¨ç´ æç›®å½•ã€‚
            # å…è®¸ç”¨æˆ·ä¼ æ–‡ä»¶åï¼Œä¹Ÿå…¼å®¹åŽ†å²è¿”å›žçš„ç»å¯¹è·¯å¾„ï¼Œä½†ä¸å…è®¸é€ƒé€¸åˆ°ç³»ç»Ÿ
            # å…¶ä»–ç›®å½•ï¼Œé¿å…ä»»æ„æ–‡ä»¶è¯»å–æˆ–é€šè¿‡ MoviePy æŽ¢æµ‹æœ¬åœ°æ•æ„Ÿæ–‡ä»¶ã€‚
            logger.warning(
                f"skip unsafe local material: {material.url}, "
                f"local_videos_dir: {local_videos_dir}, error: {str(exc)}"
            )
            continue

        ext = utils.parse_extension(material_source_path)
        try:
            # å›¾ç‰‡ç´ æç›´æŽ¥æŒ‰å›¾ç‰‡æ–¹å¼è¯»å–ï¼Œé¿å…å…ˆèµ° VideoFileClip è¯¯åˆ¤åŽè§¦å‘ä¸ç¨³å®šçš„å›žé€€åˆ†æ”¯ã€‚
            if ext in const.FILE_TYPE_IMAGES:
                clip, material_source_path = _open_image_clip_with_fallback(
                    material_source_path
                )
            else:
                clip = _open_video_clip_quietly(material_source_path)
        except Exception:
            # éžæ ‡å‡†æ‰©å±•åæˆ–æŽ¢æµ‹å¤±è´¥æ—¶å†å›žé€€åˆ°å›¾ç‰‡æ¨¡å¼ï¼Œå…¼å®¹åŽ†å²ä¸Šç›´æŽ¥ä¼ æœ¬åœ°å›¾ç‰‡è·¯å¾„çš„æƒ…å†µã€‚
            try:
                clip, material_source_path = _open_image_clip_with_fallback(
                    material_source_path
                )
            except Exception as exc:
                logger.warning(
                    f"skip unreadable local material: {material.url}, error: {str(exc)}"
                )
                continue
        try:
            width = clip.size[0]
            height = clip.size[1]
            if width < 480 or height < 480:
                logger.warning(f"low resolution material: {width}x{height}, minimum 480x480 required")
                # æŽ¢æµ‹åˆ°ä½Žåˆ†è¾¨çŽ‡ç´ æåŽç«‹å³å…³é—­èµ„æºï¼Œå¹¶ä¸”ä¸è¦æŠŠè¯¥ç´ æè¿”å›žç»™åŽç»­æµç¨‹ã€‚
                close_clip(clip)
                continue

            if ext in const.FILE_TYPE_IMAGES:
                logger.info(f"processing image: {material_source_path}")
                # æŽ¢æµ‹å°ºå¯¸æ—¶å·²ç»æ‰“å¼€è¿‡ä¸€æ¬¡ç´ æï¼Œè¿™é‡Œå…ˆé‡Šæ”¾æŽ¢æµ‹å¥æŸ„ï¼Œå†é‡æ–°åˆ›å»ºç”¨äºŽå¯¼å‡ºçš„å›¾ç‰‡ clipã€‚
                close_clip(clip)
                # Create an image clip and set its duration to 3 seconds
                clip = (
                    ImageClip(material_source_path)
                    .with_duration(clip_duration)
                    .with_position("center")
                )
                # Apply a zoom effect using the resize method.
                # A lambda function is used to make the zoom effect dynamic over time.
                # The zoom effect starts from the original size and gradually scales up to 120%.
                # t represents the current time, and clip.duration is the total duration of the clip (3 seconds).
                # Note: 1 represents 100% size, so 1.2 represents 120% size.
                zoom_clip = clip.resized(
                    lambda t: 1 + (clip_duration * 0.03) * (t / clip.duration)
                )

                # Optionally, create a composite video clip containing the zoomed clip.
                # This is useful when you want to add other elements to the video.
                final_clip = CompositeVideoClip([zoom_clip])

                # Output the video to a file.
                video_file = f"{material_source_path}.mp4"
                final_clip.write_videofile(video_file, fps=30, logger=None)
                close_clip(clip)
                close_clip(final_clip)
                material.url = video_file
                logger.success(f"image processed: {video_file}")
            else:
                # æ™®é€šè§†é¢‘ç´ æåªéœ€è¦è¯»å–å°ºå¯¸åšæ ¡éªŒï¼Œæ ¡éªŒå®ŒæˆåŽç«‹å³é‡Šæ”¾å¥æŸ„å³å¯ã€‚
                close_clip(clip)
        except Exception:
            close_clip(clip)
            raise

        valid_materials.append(material)

    return valid_materials

