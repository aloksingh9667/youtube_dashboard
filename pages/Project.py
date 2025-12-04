# --- YOUR ORIGINAL IMPORTS ---
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
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter


# ----------------- Authentication Check -----------------
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ You must login first to access this page!")
    st.stop()

# --------------------------- CONFIG ---------------------------
st.set_page_config(page_title="YouTube Studio Pro", layout="wide")

YT_API_KEY = st.secrets["YT_API_KEY"]

try:
    youtube = build("youtube", "v3", developerKey=YT_API_KEY)
except:
    youtube = None
    st.error("YouTube API not initialized.")

# --------------------------- HELPERS ---------------------------
_duration_re = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


# ----------- FIXED SAFE PARSE FUNCTION -----------
def parse_duration(s):
    if not s:
        return 0
    m = _duration_re.match(s)
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def get_channel_stats(channel_id):
    try:
        r = youtube.channels().list(
            part="snippet,contentDetails,statistics", id=channel_id
        ).execute()
        d = r["items"][0]
        return {
            "channel_id": channel_id,
            "channel_name": d["snippet"]["title"],
            "subscribers": int(d["statistics"].get("subscriberCount", 0)),
            "views": int(d["statistics"].get("viewCount", 0)),
            "total_videos": int(d["statistics"].get("videoCount", 0)),
            "uploads_playlist": d["contentDetails"]["relatedPlaylists"]["uploads"],
        }
    except:
        return {}


def get_video_ids(playlist_id, max_results=300):
    ids, next_page = [], None
    while True:
        res = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()

        ids.extend([v["contentDetails"]["videoId"] for v in res["items"]])

        if len(ids) >= max_results:
            return ids
        next_page = res.get("nextPageToken")
        if not next_page:
            break
    return ids


def get_video_details(ids):
    rows = []
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        res = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(batch)
        ).execute()

        for v in res["items"]:
            s = v["snippet"]
            stt = v["statistics"]
            cd = v["contentDetails"]

            rows.append({
                "video_id": v["id"],
                "title": s["title"],
                "views": int(stt.get("viewCount", 0)),
                "likes": int(stt.get("likeCount", 0)),
                "comments": int(stt.get("commentCount", 0)),
                "publishedAt": pd.to_datetime(s["publishedAt"]),
                "duration_s": parse_duration(cd.get("duration", "")),
                "thumbnail": s["thumbnails"]["medium"]["url"],
            })

    df = pd.DataFrame(rows)
    df["minutes"] = df["duration_s"] / 60
    df["engagement_rate"] = (df["likes"] + df["comments"]) / df["views"].replace(0, 1)
    return df


# --------------------------- NEW PDF EXPORT FUNCTION ---------------------------
def download_all_data_pdf(videos_df, channels):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>YouTube Analytics Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    # Channel Statistics
    story.append(Paragraph("<b>Channel Overview</b>", styles["Heading2"]))
    for ch in channels:
        story.append(Paragraph(
            f"- <b>{ch['channel_name']}</b>: {ch['subscribers']:,} subscribers, "
            f"{ch['views']:,} views, {ch['total_videos']:,} videos",
            styles["BodyText"]
        ))

    story.append(Spacer(1, 12))

    # Video Stats Summary
    story.append(Paragraph("<b>Overall Video Statistics</b>", styles["Heading2"]))
    story.append(Paragraph(
        f"Total Views: {videos_df['views'].sum():,}<br/>"
        f"Total Videos: {len(videos_df):,}<br/>"
        f"Avg Engagement: {videos_df['engagement_rate'].mean():.2%}",
        styles["BodyText"]
    ))

    story.append(Spacer(1, 12))

    # Top 10 Videos
    story.append(Paragraph("<b>Top 10 Most Viewed Videos</b>", styles["Heading2"]))
    top10 = videos_df.sort_values("views", ascending=False).head(10)

    for i, r in top10.iterrows():
        story.append(Paragraph(
            f"{r['title']} – {r['views']:,} views ({r['channel_name']})",
            styles["BodyText"]
        ))

    story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer


# --------------------------- UI ---------------------------
st.title("📊 YouTube Analytics Studio PRO")
st.markdown(f"Welcome, **{st.session_state['user']}** 👋")

with st.sidebar:
    st.header("Settings")

    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.rerun()

    ids_raw = st.text_area("Channel IDs (1 per line)", value="UCk8GzjMOrta8yxDcKfylJYw")
    channel_ids = [i.strip() for i in ids_raw.splitlines() if i.strip()]

    today = datetime.now(timezone.utc).date()
    start_date = st.date_input("Start Date", today - timedelta(days=30))
    end_date = st.date_input("End Date", today)

    fetch = st.button("Fetch Data")


if not fetch:
    st.stop()


# --------------------------- FETCH DATA ---------------------------
with st.spinner("Fetching channels & videos..."):
    channels = []
    frames = []

    for cid in channel_ids:
        ch = get_channel_stats(cid)
        if not ch:
            st.error(f"Invalid channel ID: {cid}")
            continue

        channels.append(ch)

        vids = get_video_ids(ch["uploads_playlist"], 500)
        df = get_video_details(vids)
        df["channel_name"] = ch["channel_name"]
        df["channel_id"] = cid

        frames.append(df)

videos_df = pd.concat(frames)
videos_df = videos_df[
    (videos_df["publishedAt"].dt.date >= start_date)
    & (videos_df["publishedAt"].dt.date <= end_date)
]

# --------------------------- METRICS ---------------------------
st.subheader("📌 Overall Metrics")
c1, c2, c3 = st.columns(3)

c1.metric("Total Views", f"{videos_df['views'].sum():,}")
c2.metric("Total Videos", len(videos_df))
c3.metric("Avg Engagement", f"{videos_df['engagement_rate'].mean():.2%}")


# --------------------------- PDF DOWNLOAD BUTTON ---------------------------
pdf_buffer = download_all_data_pdf(videos_df, channels)

st.download_button(
    label="📄 Download Full Analytics PDF",
    data=pdf_buffer,
    file_name="youtube_analytics_report.pdf",
    mime="application/pdf"
)


# --------------------------- CHANNEL COMPARISON BAR ---------------------------
st.subheader("📊 Channel Comparison Charts")

if len(channels) >= 2:
    comp = pd.DataFrame(channels)

    fig = px.bar(
        comp,
        x="channel_name",
        y=["subscribers", "views", "total_videos"],
        barmode="group",
        title="Channel Stats Comparison"
    )
    st.plotly_chart(fig, width="stretch")

    fig_radar = go.Figure()

    for _, row in comp.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row["subscribers"], row["views"], row["total_videos"]],
            theta=["Subscribers", "Views", "Videos"],
            fill="toself",
            name=row["channel_name"]
        ))

    fig_radar.update_layout(title="Channel Performance Radar")
    st.plotly_chart(fig_radar, width="stretch")


# --------------------------- VIDEO COMPARISON ---------------------------
st.subheader("🔥 Top Video Comparison")

top = videos_df.sort_values("views", ascending=False).head(15)

fig = px.bar(
    top,
    x="title",
    y="views",
    color="channel_name",
    title="Top 15 Most Viewed Videos"
)
st.plotly_chart(fig, width="stretch")


# --------------------------- SCATTER: Views vs Engagement ---------------------------
st.subheader("📈 Engagement vs Views")

fig = px.scatter(
    videos_df,
    x="views",
    y="engagement_rate",
    color="channel_name",
    hover_name="title",
    title="Engagement Rate vs Views",
    trendline="ols"
)
st.plotly_chart(fig, width="stretch")


# --------------------------- Duration vs Views ---------------------------
st.subheader("⏱ Video Duration vs Views")

fig = px.scatter(
    videos_df,
    x="minutes",
    y="views",
    color="channel_name",
    hover_name="title",
    title="Does Longer Video = More Views?"
)
st.plotly_chart(fig, width="stretch")


# --------------------------- Upload Time Heatmap ---------------------------
st.subheader("🔥 Upload Time Analysis")

videos_df["hour"] = videos_df["publishedAt"].dt.hour

heat = videos_df.groupby(["channel_name", "hour"])["views"].mean().reset_index()

fig = px.density_heatmap(
    heat,
    x="hour",
    y="channel_name",
    z="views",
    title="Average Views by Upload Hour"
)
st.plotly_chart(fig, width="stretch")


# --------------------------- WORD CLOUD ---------------------------
st.subheader("☁️ Word Cloud (Combined)")

text = " ".join(videos_df["title"].tolist())

wc = WordCloud(width=1200, height=400, background_color="white").generate(text)

fig_wc, ax = plt.subplots(figsize=(12, 4))
ax.imshow(wc)
ax.axis("off")
st.pyplot(fig_wc)

st.subheader("🎨 Channel-wise Word Clouds")

for ch in videos_df["channel_name"].unique():
    st.markdown(f"### {ch}")
    t = " ".join(videos_df[videos_df["channel_name"] == ch]["title"])

    wc = WordCloud(width=900, height=300, background_color="white").generate(t)
    fig_wc, ax = plt.subplots(figsize=(10, 3))
    ax.imshow(wc)
    ax.axis("off")
    st.pyplot(fig_wc)
