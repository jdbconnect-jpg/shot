# YouTube Shorts Official Guide Notes

Sources:

- YouTube Help: Search and discovery tips - Shorts  
  https://support.google.com/youtube/answer/11914225?co=YOUTUBE._YTVideoType%3Dshorts&hl=en-GB
- YouTube Help: Content tab analytics tips - Shorts  
  https://support.google.com/youtube/answer/12942217?co=YOUTUBE._YTVideoType%3Dshorts&hl=en

Fetched: 2026-05-17

## Core Takeaways

YouTube says Shorts recommendations are not based on a fixed preferred format. Shorts are recommended based on viewer personalisation and performance signals.

Important performance signals:

- Whether viewers choose to watch instead of swiping away.
- Average view duration.
- Average percentage viewed.
- Likes/dislikes.
- Post-watch survey feedback.
- Viewer history and topic interest.

Important discovery surfaces:

- Shorts feed.
- Home.
- Subscriptions.
- Search.
- Sounds and hashtags.
- Trends.

External factors:

- Topic interest.
- Competition from other Shorts.
- Seasonality and audience context.

## Analytics To Track

In YouTube Studio Analytics, use the Content tab and the Shorts chip.

Track:

- Views.
- Likes.
- Subscriber change.
- Shown in feed.
- How many chose to view.
- Traffic sources.
- YouTube search terms.
- Suggested videos.
- Top Shorts by views.
- Remix metrics when relevant.

## Production Implications For This Channel

### Hook

- The first 1-2 seconds must make the viewer choose to watch instead of swiping away.
- Use a clear problem or curiosity gap.
- Avoid slow intros, channel branding intros, and vague openings.

Good patterns:

- `ETF 초보가 제일 많이 하는 실수 3가지`
- `배당률만 보고 ETF 사면 여기서 꼬입니다`
- `ETF 여러 개 샀는데 사실 같은 종목일 수 있습니다`

### Retention

- One scene should carry one idea.
- Use fast but readable scene changes.
- Keep narration tight: no filler, no repeated setup.
- Put the payoff before the final seconds, then end with a concise rule.

### Viewer Satisfaction

- Do not overpromise profits.
- Keep investment disclaimer in description, not as intrusive on-screen copy.
- Avoid clickbait that the video does not answer.
- Make the final takeaway practical enough that viewers feel they gained a useful rule.

### Metadata

- Search metadata still matters, especially for evergreen finance topics.
- Title should contain the actual searchable topic.
- Description should include the key lesson, ETF topic, and disclaimer.
- Tags are secondary, but should include topic terms such as ETF, ETF 투자, 투자초보, 미국 ETF, 배당 ETF, 장기투자.

### Thumbnail

- Shorts feed often starts from the video itself, but thumbnails matter for Home/Search/channel pages.
- Thumbnail text must be readable and not broken.
- Use one strong claim, not too many text blocks.
- Keep Korean text composed locally when model-generated text is unreliable.
- Every Shorts production run should include a matching thumbnail and metadata thumbnail_path.

## Current Shorts Review

Reviewed current video:

- `media_agent/data_shorts/renders/scr_20260517_etf_beginner_mistakes_final_720p.mp4`
- Topic: 초보자가 ETF 고를 때 제일 많이 하는 실수
- Duration: about 46 seconds
- Layout: black top hook, central OpenAI-generated panda scene, lower subtitle band, no progress bar
- Voice: ElevenLabs Taehyung confirmed in logs

### What Already Fits

- Strong topic interest: ETF beginner mistakes is evergreen and searchable.
- Clear hook: starts with a direct beginner mistake premise.
- Good length: under 60 seconds.
- Clear structure: 3 mistakes plus conclusion.
- Practical payoff: choose by purpose, not popularity or headline yield.
- Low policy risk: investment education tone, not direct buy/sell recommendation.

### Recommended Improvements

1. Improve the first 1-2 seconds.
   - Current opening is clear, but can be sharper.
   - Better hook: `ETF 처음 살 때, 이 3개 실수하면 계좌가 꼬입니다.`
   - Reason: stronger consequence gives viewers a reason not to swipe.

2. Make visual scenes more action-specific.
   - Current generated scenes are clean, but some can feel generic.
   - Each scene should visually show the mistake:
     - high dividend lure vs hidden risk
     - overlapping ETF holdings
     - small fee compounding over time

3. Add a stronger final loop or rewatch cue.
   - End with a compact checklist:
     - `배당? 성장? 안정? 목적 먼저.`
   - This gives a memorable closing rule.

4. Track analytics after upload.
   - Specifically check:
     - Shown in feed
     - How many chose to view
     - Average percentage viewed
     - Likes/subscribers
   - If chose-to-view is weak, change hook/title/first frame.
   - If retention drops after scene 2, shorten explanations or increase visual contrast.

5. Use the thumbnail only as support.
   - Shorts feed performance depends heavily on the video start itself.
   - Do not rely on thumbnail to compensate for a slow first second.

## Checklist Before Upload

- Video is vertical 9:16.
- Duration is under 60 seconds.
- First second clearly states the problem.
- No slow intro.
- No broken Korean text.
- Audio is clear and uses Taehyung voice.
- Captions are readable on mobile.
- Description includes investment disclaimer.
- Metadata includes searchable topic terms.
- After upload, review Shorts analytics rather than judging only by views.
