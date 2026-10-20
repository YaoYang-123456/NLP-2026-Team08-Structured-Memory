"""Make a clearly marked local synthetic demo from nine checked slides and WAVs."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import wave


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ffmpeg", required=True)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--font", type=Path, required=True)
    a = p.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    output = a.package / "video/第8队-8分钟-合成配音演示样片.mp4"
    if output.exists():
        raise SystemExit("Refusing to replace existing video")
    durations = []
    for i in range(1, 10):
        with wave.open(str(a.audio / f"page-{i:02}.wav")) as w:
            durations.append(w.getnframes() / w.getframerate())
    frames = [math.ceil(s * 10) for s in durations]
    if sum(frames) > 4800:
        raise SystemExit("Narration exceeds eight minutes; revise the script first")
    for i in range(4800 - sum(frames)):
        frames[i % 9] += 1
    # Work-relative font avoids Windows drive-colon escaping in filter syntax.
    import shutil
    shutil.copyfile(a.font, a.work / "voice-label-font.ttc")
    (a.work / "label.txt").write_text("合成配音演示样片｜非组员录音｜未提交", encoding="utf-8")
    filter_text = (
        "drawtext=fontfile=voice-label-font.ttc:textfile=label.txt:"
        "fontcolor=0x596B7B:fontsize=17:x=60:y=7"
    )
    records = []
    for i, (seconds, count) in enumerate(zip(durations, frames), 1):
        segment = a.work / f"segment-{i:02}.mp4"
        command = [
            a.ffmpeg, "-nostdin", "-n", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", "10",
            "-i", str(a.package / f"preview/slide-{i:02}.png"),
            "-i", str(a.audio / f"page-{i:02}.wav"),
            "-vf", filter_text, "-af", "apad", "-t", str(count / 10),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-threads", "4",
            "-c:a", "aac", "-b:a", "96k", "-ar", "44100",
            "-movflags", "+faststart", str(segment),
        ]
        subprocess.run(command, cwd=a.work, check=True)
        records.append({"page": i, "wav_seconds": seconds, "video_seconds": count / 10,
                        "frames": count, "synthetic": True})
    (a.work / "segments.txt").write_text(
        "".join(f"file 'segment-{i:02}.mp4'\n" for i in range(1, 10)), encoding="utf-8"
    )
    subprocess.run([
        a.ffmpeg, "-nostdin", "-n", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", "segments.txt",
        "-c:v", "copy", "-af", "apad", "-t", "480", "-c:a", "aac",
        "-b:a", "96k", "-movflags", "+faststart", str(output),
    ], cwd=a.work, check=True)
    check = subprocess.run([
        a.ffmpeg, "-nostdin", "-hide_banner", "-i", str(output),
        "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    (a.package / "checks/video-decode.txt").write_text(check.stderr, encoding="utf-8")
    if check.returncode:
        raise SystemExit("Video decode failed")
    timing = {"voice": "Microsoft Huihui Desktop", "rate": -1,
              "human_rehearsal": False, "submitted": False,
              "raw_narration_seconds": sum(durations), "target_video_seconds": 480,
              "total_frames": sum(frames), "decode_returncode": check.returncode,
              "pages": records}
    (a.package / "checks/narration-timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(timing, ensure_ascii=False))


if __name__ == "__main__":
    main()
