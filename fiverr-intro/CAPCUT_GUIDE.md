# CapCut Edit Guide

Assemble your Fiverr intro video. Target final length: **45–55 seconds**.

---

## 1. Create project

1. Open **CapCut desktop** (free download from capcut.com)
2. **New project** → Aspect ratio **16:9** → Resolution **1080p** (or 720p)

---

## 2. Import clips

Import from `fiverr-intro/raw/`:

- `block-a-hook.mp4`
- `clip1-intake.mp4`
- `clip2-scoring.mp4`
- `clip3-shortlist.mp4`
- `block-c-cta.mp4`

---

## 3. Timeline layout

Place clips on the video track in this order:

```
| Block A | Clip 1 | Clip 2 | Clip 3 | Block C |
| 0-12s   | 12-19s | 19-26s | 26-35s | 35-50s  |
```

Trim dead air at the start and end of each clip.

---

## 4. Audio

- Block A and Block C: use audio from face clips
- Block B section (0:12–0:35): add voiceover
  - Record in CapCut (**Audio → Record**), or
  - Import `block-b-voiceover.wav` if recorded separately
- Align voiceover with screen montage

---

## 5. Subtitles

**Option A — Auto captions (easiest)**

1. Select all clips → **Text → Auto captions**
2. Language: **English**
3. Fix spellings: **Acreva**, **HireFlow**, **Claude**, **OpenAI**

**Option B — Import SRT**

1. **Text → Import subtitles**
2. Use [`subtitles.srt`](subtitles.srt)
3. Adjust timing if needed after trimming clips

---

## 6. Optional polish

On the screen section (0:12–0:35), add lower-third text:

```
CV Screening · Chatbots · Email Automation
```

Skip background music, or use CapCut royalty-free library at very low volume (-20 dB under voice).

---

## 7. Export

1. **Export** → Format **MP4**
2. Resolution: **1080p** or **720p** (min 1280×720 for Fiverr)
3. Frame rate: **30 fps**
4. Filename: **`acreva-intro.mp4`**
5. Save to: `fiverr-intro/export/acreva-intro.mp4`

---

## 8. QA before upload

- [ ] Total length 20–60 seconds (aim 45–55)
- [ ] You appear and speak at start AND end
- [ ] No email, phone, or social handles visible
- [ ] Subtitles readable with sound muted
- [ ] Audio clear with eyes closed
- [ ] Plays correctly in VLC or Windows Media Player

If Fiverr rejects the file, re-encode with **HandBrake** (Web → Gmail Large 720p30).

Next step: [`UPLOAD_CHECKLIST.md`](UPLOAD_CHECKLIST.md)
