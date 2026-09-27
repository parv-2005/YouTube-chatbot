from youtube_transcript_api import YouTubeTranscriptApi


def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]

    return None


def get_transcript(url):
    video_id = get_video_id(url)

    if not video_id:
        return {"error": "Invalid YouTube URL"}

    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)

        result = []

        for item in transcript:
            result.append({
                "text": item.text,
                "start": item.start,
                "duration": item.duration
            })

        return result

    except Exception as e:
        return {"error": str(e)}