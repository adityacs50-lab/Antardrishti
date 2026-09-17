# Remotion demo video (SIH26165)

Built with [Remotion](https://github.com/remotion-dev/remotion) — programmatic React video.

## Render the judge MP4

```powershell
cd prahari\demo-video
npm install
npx remotion render src/index.ts PrahariDemo out/prahari-sih26165-demo.mp4 --browser-executable="C:\Program Files\Google\Chrome\Application\chrome.exe" --timeout=120000
```

Output: `out/prahari-sih26165-demo.mp4` (~105 seconds, 1920×1080).

Also copied to `../demo/prahari-sih26165-demo.mp4` after a successful render.

## Preview in Remotion Studio

```powershell
npm run studio
```

## Scenes

1. Title / thesis  
2. Triage + Potential ≠ severity  
3. Report A — cut finger (low potential)  
4. Report B — PSIF / Energy Isolation  
5. Report detail — rule trace  
6. Precursor map — accumulation  
7. Life-Saving Rules + close  
