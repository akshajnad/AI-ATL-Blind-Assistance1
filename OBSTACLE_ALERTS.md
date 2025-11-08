# Obstacle Alert System

## Overview

The **Obstacle Alert System** is an intelligent, proactive safety feature that continuously monitors the environment and provides audio alerts when obstacles are approaching. This system works in parallel with the conversational AI (Kora) to provide real-time safety warnings without requiring user interaction.

## Key Features

### 1. **Distance-Based Danger Levels**
The system classifies obstacles into four danger levels based on their distance from the camera:

| Danger Level | Distance | Relative Depth | Color Code | Alert Behavior |
|-------------|----------|----------------|------------|----------------|
| **CRITICAL** | < 2m | ≤ 0.25 | 🔴 Red | Immediate urgent alert |
| **HIGH** | 2-4m | 0.25-0.50 | 🟠 Orange/Yellow | Caution alert |
| **MEDIUM** | 4-8m | 0.50-0.75 | 🟡 Yellow | Alert only if approaching |
| **LOW** | > 8m | > 0.75 | 🟢 Teal | No alert (safe distance) |

These danger levels are aligned with the visual color coding system used in the frontend camera overlay.

### 2. **Approach Detection**
The system tracks objects over time to detect when they are approaching (getting closer). This prevents alerts for static objects at medium distances while ensuring users are warned when obstacles are moving toward them.

- Objects are tracked across multiple frames
- Initial distance is recorded when first detected
- An object is considered "approaching" if distance decreases by 10% or more
- Medium-danger objects only trigger alerts if they're approaching

### 3. **Smart Deduplication (No Spam)**
The alert system implements multiple layers of spam prevention:

- **Global Throttling**: Minimum 5 seconds between any alerts
- **Per-Object Cooldown**: Same object won't trigger alerts within 30 seconds
- **Position Tracking**: Objects are identified by label + position (quadrant)
- **Memory Cleanup**: Objects not seen for 10 seconds are forgotten

This ensures users receive timely alerts without being overwhelmed by repeated warnings about the same obstacle.

### 4. **Priority-Based Alerting**
When multiple obstacles are detected, the system prioritizes alerts based on:

1. **Danger level** (Critical > High > Medium)
2. **Object type weight** (Vehicles > People > Static objects)
3. **Approach status** (Approaching objects are prioritized)
4. **Confidence score** (Higher confidence detections first)

The highest-risk object is selected for alerting each frame.

### 5. **Object-Specific Recommendations**
Alerts include actionable recommendations based on object type and danger level:

| Object Type | Critical Alert | High Alert |
|------------|----------------|------------|
| Person | "Stop" | "Slow down" |
| Car/Truck/Bus | "Move aside immediately" | "Move to the side" |
| Bicycle/Motorcycle | "Stop" | "Be careful" |
| Pole/Curb | "Stop" | "Avoid ahead" |

## Alert Examples

### Critical Danger (< 2m)
```
"Alert! Person very close on your center. Stop!"
"Alert! Car very close on your left. Move aside immediately!"
```

### High Danger (2-4m)
```
"Person approaching on your center, about four meters. Slow down."
"Car approaching on your right, about four meters. Move to the side."
```

### Medium Danger (4-8m, approaching only)
```
"Bicycle approaching from left, about eight meters."
"Pole approaching from center, about eight meters."
```

## Technical Architecture

### Components

1. **`ObstacleAlertSystem`** (`ElevenLabs/obstacle_alert.py`)
   - Main alert processor with tracking and deduplication
   - Configurable timing parameters
   - Integrates with ElevenLabs TTS for audio output

2. **`DangerLevel`** (utility class)
   - Classifies distances into danger categories
   - Aligned with frontend color coding thresholds

3. **`TrackedObject`** (dataclass)
   - Stores object state across frames
   - Tracks approach status and alert history

### Integration Points

The obstacle alert system is integrated at multiple levels:

1. **Main Vision API** (`vision/main.py`)
   - Processes every frame through the alert system
   - Alerts are triggered independently of user queries

2. **SnowFlake Server** (`SnowFlake/server.py`)
   - Alternative deployment for separate alert processing
   - Used when running distributed architecture

3. **Camera Demo** (`vision/run_camera.py`)
   - Local development and testing
   - Standalone camera loop with alerts

## Configuration

The system can be configured with three timing parameters:

```python
alert_system = ObstacleAlertSystem(
    min_alert_interval_s=5.0,   # Minimum seconds between any alerts
    object_memory_s=10.0,        # How long to remember objects (seconds)
    alert_cooldown_s=30.0,       # Don't re-alert same object within this time
)
```

### Recommended Settings

| Use Case | min_alert_interval | object_memory | alert_cooldown |
|----------|-------------------|---------------|----------------|
| **Default** | 5.0s | 10.0s | 30.0s |
| **High Traffic** | 3.0s | 8.0s | 20.0s |
| **Quiet Areas** | 7.0s | 15.0s | 45.0s |
| **Testing** | 2.0s | 10.0s | 10.0s |

## Object Weights

Different object types have different risk weights:

| Object Type | Weight | Rationale |
|------------|--------|-----------|
| Truck/Bus | 1.4 | Large, heavy, high danger |
| Car | 1.3 | Common vehicle threat |
| Motorcycle | 1.2 | Fast-moving vehicle |
| Bicycle | 1.1 | Moving obstacle |
| Person | 1.0 | Baseline mobile obstacle |
| Curb | 0.7 | Trip hazard |
| Crosswalk | 0.6 | Navigation aid |
| Pole | 0.4 | Static obstacle |
| Bench | 0.2 | Low-priority static object |

## Usage

### Running the Test Suite

Test the alert system with simulated scenarios:

```bash
python test_obstacle_alerts.py
```

This demonstrates:
- ✓ Approach detection
- ✓ Danger level classification
- ✓ Alert deduplication
- ✓ Alert prioritization
- ✓ Smart throttling

### Starting the Vision Server with Alerts

```bash
cd vision
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The obstacle alert system is automatically active and will process every frame sent to the `/analyze` endpoint.

### Running Camera Demo with Alerts

```bash
python vision/run_camera.py
```

This opens your camera and provides real-time obstacle alerts.

## How It Works

### Frame Processing Flow

```
1. Camera Frame Captured
   ↓
2. YOLO Object Detection + MiDaS Depth Estimation
   ↓
3. Frame sent to /analyze endpoint
   ↓
4. Vision Pipeline processes frame
   ↓
5. ObstacleAlertSystem.process_frame() called
   ↓
6. Objects tracked and distances compared
   ↓
7. Danger levels calculated
   ↓
8. Alert candidate selected (highest risk)
   ↓
9. Deduplication checks applied
   ↓
10. Alert message generated (if needed)
    ↓
11. ElevenLabs TTS speaks alert
    ↓
12. User hears warning
```

### Parallel Operation

The obstacle alert system operates **in parallel** with conversational AI:

- **User asks**: "Hey Kora, what's in front of me?"
- **Kora responds**: "I see a bench and a person to your left..."
- **Meanwhile, alert system**: Continuously monitoring all objects
- **If critical**: "Alert! Car very close on your right. Move aside immediately!"

This ensures safety alerts are never delayed by conversation.

## Distance Calibration

The system uses normalized depth values (0-1) from MiDaS. Distance buckets are approximate:

| Relative Depth | Approximate Distance | Calibration Notes |
|----------------|---------------------|-------------------|
| 0.25 | ~2 meters | Critical threshold |
| 0.50 | ~4 meters | High danger threshold |
| 0.75 | ~8 meters | Medium danger threshold |
| > 0.75 | 10+ meters | Safe distance |

For more accurate metric distances, the system can be enhanced with stereo camera calibration or known object sizes.

## Future Enhancements

Potential improvements to the alert system:

1. **Velocity Estimation**: Detect object speed for better predictions
2. **Trajectory Prediction**: Estimate collision paths
3. **Multi-Camera Support**: 360° coverage
4. **Haptic Feedback**: Vibration alerts for quiet environments
5. **Metric Depth**: Calibrated real-world distances
6. **Alert Zones**: Customizable danger thresholds per environment
7. **Voice Customization**: Different alert voices for different danger levels
8. **Alert History**: Review recent alerts
9. **Machine Learning**: Adaptive thresholds based on user feedback

## Troubleshooting

### No alerts are being spoken

1. Check ElevenLabs API key is configured
2. Verify audio output is not muted
3. Check logs for `[OBSTACLE ALERT]` messages
4. Ensure objects are being detected (check YOLO output)

### Too many alerts (spam)

1. Increase `min_alert_interval_s` (e.g., 7.0 seconds)
2. Increase `alert_cooldown_s` (e.g., 45.0 seconds)
3. Check if multiple objects are being detected as separate instances

### Alerts are delayed

1. Decrease `min_alert_interval_s` (e.g., 3.0 seconds)
2. Check system performance (CPU/GPU usage)
3. Verify camera frame rate is adequate (target: 10 FPS)

### Missing critical alerts

1. Check danger level thresholds are appropriate
2. Verify depth estimation is working (MiDaS output)
3. Review object detection confidence scores
4. Check `alert_cooldown_s` isn't too long

## Safety Considerations

⚠️ **Important Safety Notes**:

- This system is an **assistive tool**, not a replacement for traditional mobility aids
- Always use with a cane, guide dog, or human assistance as appropriate
- System accuracy depends on lighting, camera quality, and object visibility
- False negatives are possible - the system may not detect all obstacles
- False positives may occur - verify alerts when safe to do so
- Test in controlled environments before relying on the system
- Keep software and models updated for best performance

## License

This obstacle alert system is part of the AI-ATL Blind Assistance project and follows the same license as the main repository.
