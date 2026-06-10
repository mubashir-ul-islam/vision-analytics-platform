# vision-heatmap-counter

Shop analytics system using YOLO26 — live person counting + foot-traffic heatmap from a ceiling-mounted camera, served as a web dashboard.

## Features

- **Person detection** — bounding boxes with tracking IDs via YOLO26 + ByteTrack/BoT-SORT
- **Heatmap** — cumulative foot-traffic overlay showing the busiest areas
- **Live stats** — current occupancy, total unique visitors, session time, FPS
- **Web dashboard** — two side-by-side live streams, all parameters adjustable without restart
- **Camera switching** — switch between built-in and USB cameras from the UI
- **Docker** — runs fully containerized with GPU support

## Quick Start

```bash
docker compose up --build
```

Open **http://localhost:8000**

## Dashboard Controls

| Control | Description |
|---------|-------------|
| Camera / Resolution | Switch between cameras and set resolution |
| YOLO Model | n/s/m/l/x variants — trade speed for accuracy |
| Device | Auto / CPU / CUDA:0 |
| Confidence | Detection confidence threshold (0.05–0.95) |
| IoU Threshold | NMS overlap threshold |
| Tracker | ByteTrack (fast) or BoT-SORT (robust to occlusion) |
| Track Buffer | Frames to hold a lost ID before expiring (~2s at 30fps = 60) |
| Frame Stride | Process every Nth frame — increase if CPU-bound |
| Colormap | Heatmap color scheme |
| Blend Alpha | Heatmap overlay intensity |

## Model Weights

Models auto-download on first run:

| Model | Size | Best For |
|-------|------|----------|
| `yolo26n.pt` | ~5 MB | CPU / edge, real-time |
| `yolo26s.pt` | ~11 MB | Balanced |
| `yolo26m.pt` | ~42 MB | Higher accuracy |
| `yolo26l/x.pt` | 80MB+ | Maximum accuracy |

## Notes for Ceiling Cameras

- The camera covers the full shop floor so **occupancy** = number of unique track IDs visible in the current frame
- **Total visitors** = count of unique IDs seen since session start (new ID when someone re-enters after `track_buffer` frames)
- Use **BoT-SORT** if people frequently occlude each other (aisles, queues)
- Increase **Track Buffer** to avoid double-counting people who briefly leave camera view
