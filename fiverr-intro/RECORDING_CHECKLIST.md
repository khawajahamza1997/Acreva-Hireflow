# Recording Checklist

## Before filming

- [ ] Script ready — open [`SCRIPT.txt`](SCRIPT.txt)
- [ ] HireFlow demo loaded (candidates scored, shortlist visible)
- [ ] **Demo mode ON** (Streamlit sidebar or Next.js Outreach page)
- [ ] Quiet room, notifications off
- [ ] Browser at 100% zoom, personal tabs closed

---

## OBS Studio setup (recommended)

1. Download from https://obsproject.com and install
2. **Settings → Video:** Base 1920×1080, Output 1920×1080, 30 FPS
3. **Settings → Output → Recording:** Format MP4, Encoder x264
4. Add **Display Capture** source for screen clips
5. Add **Video Capture Device** source for face clips

---

## Screen clips (3 files, ~7 sec each)

Record separately. Save as:

| File | What to show |
|------|--------------|
| `clip1-intake.mp4` | CV upload or candidate list with parsed profiles |
| `clip2-scoring.mp4` | Job description + AI scores visible |
| `clip3-shortlist.mp4` | Shortlist tab, then Outreach email preview |

**Tips:** Move mouse slowly. Pause 1 second on scores and shortlist names.

### Xbox Game Bar (alternative)

1. Open HireFlow in Chrome
2. Press `Win + G` → Record
3. Stop after each scene, save clip, repeat for all 3

---

## Face clips (2 files)

| File | Script block | Length |
|------|--------------|--------|
| `block-a-hook.mp4` | Block A in SCRIPT.txt | ~12 sec |
| `block-c-cta.mp4` | Block C in SCRIPT.txt | ~10 sec |

**Setup:**

- Face a window or desk lamp (light in front, not behind)
- Chest-up framing, neutral background, plain shirt
- Look at camera lens, not the screen
- Record A and C back-to-back in same session

---

## Block B voiceover (optional separate audio)

Record `block-b-voiceover.wav` while watching your 3 screen clips, OR record voice live in CapCut over the montage.

Read Block B from SCRIPT.txt (~22 seconds).

---

## Raw files folder

Save everything to:

```
fiverr-intro/raw/
  block-a-hook.mp4
  block-b-voiceover.wav   (optional)
  block-c-cta.mp4
  clip1-intake.mp4
  clip2-scoring.mp4
  clip3-shortlist.mp4
```

Next step: [`CAPCUT_GUIDE.md`](CAPCUT_GUIDE.md)
