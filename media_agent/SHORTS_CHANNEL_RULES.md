# Shorts Channel Fixed Rules

These rules are fixed defaults for ETF shorts production. Apply them unless the user explicitly asks for a one-off exception.

## Voice

- Primary TTS must be ElevenLabs voice: **Taehyung - Natural, Friendly and Clear**.
- Voice ID: `m3gJBS8OofDJfycyA2Ip`.
- Ignore generic `ELEVENLABS_VOICE_ID` overrides for shorts unless `MEDIA_AGENT_ALLOW_CUSTOM_ELEVENLABS_VOICE=1` is explicitly set for a one-off render.
- If ElevenLabs synthesis fails, stop and surface the reason before final delivery. Do not silently present a fallback voice as final.

## Panda Presenter

- Keep the panda face consistent with the YouTube channel identity across every generated image.
- Face lock: young male panda presenter, round soft white face, large black ears, clear black eye patches, round black glasses, warm brown eyes, small friendly smile, trustworthy but approachable expression.
- Do not change face proportions, glasses shape, eye-patch layout, or overall character age impression between scenes.
- If a channel profile/header reference image is available later, use it as the highest-priority visual reference.

## Wardrobe And Gesture

- Wardrobe, pose, and gesture are flexible. Change them freely to match each scene's story, emotion, and composition.
- Only the face identity is locked. Do not treat clothing, props, posture, or gesture as fixed character requirements.
- The generated background should match the narration and the male voice, while the panda explains or reacts to the image rather than dominating it.

## Layout

- Use the reference short layout when requested: black top title area, yellow emphasis, central visual, readable white subtitle box.
- Remove the bottom progress bar from all final renders.
- Keep subtitle width readable and avoid text overlap.
