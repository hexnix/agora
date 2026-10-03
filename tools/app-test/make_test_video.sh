#!/bin/sh
# Makes the made-up film the player test uses (fixtures/made-up-film.mkv): 40 s of a dark, slowly moving colour gradient (looks like a film frame in screenshots) with a tone,
# VP9 + Opus (the test browser can't play H.264), and two English subtitle tracks, the second named "SDH".
# Every line is invented. Needs ffmpeg.
set -e
cd "$(dirname "$0")/fixtures"
cat > /tmp/agora-subs-a.srt <<'S'
1
00:00:02,000 --> 00:00:04,500
Nobody in this room reads
past the first page.

2
00:00:06,000 --> 00:00:08,000
Then we write a shorter report.

3
00:00:15,000 --> 00:00:17,500
The numbers were never the problem.

4
00:00:24,000 --> 00:00:26,000
Bring the candor, leave the timing.

5
00:00:33,000 --> 00:00:35,000
That's the last line of the film.
S
cat > /tmp/agora-subs-b.srt <<'S'
1
00:00:01,000 --> 00:00:01,800
[papers rustling]

2
00:00:02,000 --> 00:00:04,500
Nobody in this room reads
past the first page.

3
00:00:20,000 --> 00:00:21,000
[door closes]
S
ffmpeg -loglevel error -y -f lavfi -i 'gradients=s=480x270:c0=0x0f1b33:c1=0x8a4b2a:c2=0x1f3d3a:nb_colors=3:x0=0:y0=0:x1=480:y1=270:speed=0.004:duration=40:rate=24,vignette=PI/4,noise=alls=6:allf=t' -f lavfi -i sine=frequency=330:duration=40 \
  -i /tmp/agora-subs-a.srt -i /tmp/agora-subs-b.srt -map 0 -map 1 -map 2 -map 3 \
  -c:v libvpx-vp9 -b:v 120k -deadline realtime -cpu-used 8 -c:a libopus -b:a 24k -c:s srt \
  -metadata:s:s:0 language=eng -metadata:s:s:1 language=eng -metadata:s:s:1 title=SDH made-up-film.mkv
rm /tmp/agora-subs-a.srt /tmp/agora-subs-b.srt
