import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import plotly.express as px
from googleapiclient.discovery import build

# ----------------- Authentication Check -----------------
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ You must login first to access this page!")
    st.stop()

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="YouTube Studio (Clean Version)", layout="wide")

YT_API_KEY = os.environ.get("YT_API_KEY", "AIzaSyBr6ssKJCQi4ORaU9bIgGAb3cOaoo2psiI")

if not YT_API_KEY:
    st.warning("YT_API_KEY not set.")

try:
    youtube = build("youtube", "v3", developerKey=YT_API_KEY) if YT_API_KEY else None
except Exception as e:
    st.error(f"Error creating YouTube client: {e}")
    youtube = None

# ---------------------------
# Helpers
# ---------------------------
_duration_re = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

def parse_duration(duration_str: str) -> int:
    m = _duration_re.match(duration_str or "")
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)

def get_channel_stats(channel_id: str) -> Dict[str, Any]:
    if not youtube:
        return {}
    try:
        resp = youtube.channels().list(
            part="snippet,contentDetails,statistics", id=channel_id
        ).execute()
        items = resp.get("items", [])
        if not items:
            return {}
        d = items[0]
        return {
            "channel_id": channel_id,
            "channel_name": d["snippet"]["title"],
            "subscribers": int(d.get("statistics", {}).get("subscriberCount", 0)),
            "views": int(d.get("statistics", {}).get("viewCount", 0)),
            "total_videos": int(d.get("statistics", {}).get("videoCount", 0)),
            "uploads_playlist": d.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
        }
    except Exception as e:
        st.error(f"Error fetching channel {channel_id}: {e}")
        return {}

def get_video_ids(playlist_id: str, max_results=300):
    if not youtube:
        return []
    ids = []
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=next_page
        ).execute()
        for it in resp.get("items", []):
            ids.append(it["contentDetails"]["videoId"])
            if len(ids) >= max_results:
                return ids
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return ids

def get_video_details(video_ids: List[str]):
    if not youtube or not video_ids:
        return pd.DataFrame()
    rows = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(batch)
        ).execute()
        for v in resp.get("items", []):
            snip = v["snippet"]
            stats = v.get("statistics", {})
            cd = v.get("contentDetails", {})
            rows.append({
                "video_id": v["id"],
                "title": snip["title"],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "publishedAt": pd.to_datetime(snip["publishedAt"]),
                "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url"),
                "duration_s": parse_duration(cd.get("duration", "")),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["minutes"] = df["duration_s"] / 60
        df["engagement_rate"] = (df["likes"] + df["comments"]) / df["views"].replace(0, pd.NA)
    return df

# ---------------------------
# UI
# ---------------------------
st.title("YouTube Analytics Studio")
st.markdown(f"Welcome, {st.session_state['user']}!")

with st.sidebar:
    st.header("Controls")

    # ----------------- Logout -----------------
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.success("✅ Logged out successfully!")
        st.rerun()

    st.subheader("Channel Inputs")
    channel_ids_raw = st.text_area(
        "Channel IDs (one per line)", value="UCk8GzjMOrta8yxDcKfylJYw"
    )
    channel_ids = [c.strip() for c in channel_ids_raw.splitlines() if c.strip()]

    utc_today = datetime.now(timezone.utc).date()
    start_default = utc_today - timedelta(days=30)
    start_date = st.date_input("Start date", start_default)
    end_date = st.date_input("End date", utc_today)

    fetch = st.button("Fetch / Refresh")

if not fetch:
    st.info("Enter channel IDs and click Fetch.")
    st.stop()

# ---------------------------
# Fetch data
# ---------------------------
with st.spinner("Fetching..."):
    channels = []
    frames = []
    for cid in channel_ids:
        ch = get_channel_stats(cid)
        if not ch:
            st.warning(f"Channel {cid} not found.")
            continue
        channels.append(ch)
        vids = get_video_ids(ch["uploads_playlist"], 500)
        df = get_video_details(vids)
        if df.empty:
            continue
        df["channel_id"] = cid
        df["channel_name"] = ch["channel_name"]
        frames.append(df)

    if not frames:
        st.error("No data fetched.")
        st.stop()

videos_df = pd.concat(frames, ignore_index=True)
videos_df = videos_df[
    (videos_df["publishedAt"].dt.date >= start_date)
    & (videos_df["publishedAt"].dt.date <= end_date)
]

# ---------------------------
# Metrics
# ---------------------------
left, right = st.columns([3, 1])
total_views = int(videos_df["views"].sum())
total_videos = len(videos_df)
avg_eng = float(videos_df["engagement_rate"].mean(skipna=True) or 0)

left.metric("Total Views", f"{total_views:,}")
left.metric("Total Videos", total_videos)
left.metric("Avg Engagement", f"{avg_eng:.2%}")

# ---------------------------
# Comparison
# ---------------------------
st.subheader("Channel Comparison (No AI)")
if len(channels) >= 2:
    c1, c2 = channels[0], channels[1]
    st.write(f"### {c1['channel_name']} vs {c2['channel_name']}")
    comp_df = pd.DataFrame({
        "Metric": ["Subscribers", "Total Views", "Videos"],
        c1["channel_name"]: [c1["subscribers"], c1["views"], c1["total_videos"]],
        c2["channel_name"]: [c2["subscribers"], c2["views"], c2["total_videos"]],
    })
    st.dataframe(comp_df)
else:
    st.info("Enter 2 channel IDs for comparison.")

# ---------------------------
# Charts
# ---------------------------
st.subheader("Views by Day")
daily = videos_df.assign(date=videos_df["publishedAt"].dt.date).groupby("date")["views"].sum()
fig = px.line(daily, title="Views by Date")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Top Videos")
top = videos_df.sort_values("views", ascending=False).head(20)
for _, r in top.iterrows():
    with st.expander(r["title"][:70]):
        st.write(f"Views: {r['views']:,}")
        st.write(f"Engagement: {r['engagement_rate']:.2%}")
        if r["thumbnail"]:
            st.image(r["thumbnail"], width=240)

st.subheader("Word Cloud")
text = " ".join(videos_df["title"].tolist())
wc = WordCloud(width=900, height=300, background_color="white").generate(text)
fig_wc, ax = plt.subplots(figsize=(12, 3))
ax.imshow(wc, interpolation='bilinear')
ax.axis("off")
st.pyplot(fig_wc)
