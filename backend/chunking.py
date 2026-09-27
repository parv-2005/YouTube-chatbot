from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_chunks(transcript, video_id):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = []
    current_text = ""
    start_time = None
    end_time = None

    for item in transcript:
        text = item["text"]

        if start_time is None:
            start_time = item["start"]

        current_text += " " + text
        end_time = item["start"] + item["duration"]

        # Create chunk when text becomes large enough
        if len(current_text) >= 500:
            split_texts = splitter.split_text(current_text)

            for split_text in split_texts:
                chunks.append({
                    "text": split_text,
                    "video_id": video_id,
                    "start_time": start_time,
                    "end_time": end_time
                })

            current_text = ""
            start_time = None

    # Add remaining text
    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "video_id": video_id,
            "start_time": start_time,
            "end_time": end_time
        })

    return chunks