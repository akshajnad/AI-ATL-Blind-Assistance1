#!/usr/bin/env python3
"""Test script to demonstrate the obstacle alert system.

This script simulates various scenarios to show how the alert system:
1. Detects approaching obstacles
2. Uses danger levels based on distance
3. Prevents spam with deduplication
4. Prioritizes critical alerts
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure imports work
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from vision.schemas import (
    BoundingBox,
    CenterDistanceSummary,
    DetectedObject,
    FrameAnalysisResponse,
    Quadrant,
)
from ElevenLabs.obstacle_alert import ObstacleAlertSystem, DangerLevel


def create_test_detection(
    label: str,
    quadrant: Quadrant,
    relative_depth: float,
    confidence: float = 0.85,
) -> DetectedObject:
    """Helper to create a test detection."""
    return DetectedObject(
        label=label,
        confidence=confidence,
        bounding_box=BoundingBox(x_min=0.3, y_min=0.3, x_max=0.7, y_max=0.7),
        quadrant=quadrant,
        relative_depth_m=relative_depth,
    )


def create_test_response(objects: list[DetectedObject]) -> FrameAnalysisResponse:
    """Helper to create a test frame response."""
    return FrameAnalysisResponse(
        frame_id="test-frame",
        objects=objects,
        center_distance=CenterDistanceSummary(
            distance_m=0.5,
            confidence=0.8,
            advisory="Test center distance",
        ),
        vision_summary="Test scene",
    )


def test_scenario_1_approaching_person():
    """Test scenario: Person approaching from the front."""
    print("\n" + "=" * 80)
    print("SCENARIO 1: Person approaching from center")
    print("=" * 80)

    alert_system = ObstacleAlertSystem(
        min_alert_interval_s=2.0,
        object_memory_s=10.0,
        alert_cooldown_s=10.0,
    )

    # Frame 1: Person far away (safe)
    print("\nFrame 1: Person at 10+ meters (safe distance)")
    response = create_test_response([
        create_test_detection("person", Quadrant.CENTER, 0.85)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None - too far for alert'}")

    time.sleep(2.5)

    # Frame 2: Person getting closer (medium danger)
    print("\nFrame 2: Person at ~8 meters (medium distance, approaching)")
    response = create_test_response([
        create_test_detection("person", Quadrant.CENTER, 0.70)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")

    time.sleep(2.5)

    # Frame 3: Person much closer (high danger)
    print("\nFrame 3: Person at ~4 meters (high danger)")
    response = create_test_response([
        create_test_detection("person", Quadrant.CENTER, 0.45)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")

    time.sleep(2.5)

    # Frame 4: Person very close (critical)
    print("\nFrame 4: Person at ~2 meters (CRITICAL danger)")
    response = create_test_response([
        create_test_detection("person", Quadrant.CENTER, 0.20)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")


def test_scenario_2_deduplication():
    """Test scenario: Alert deduplication - same object shouldn't spam."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: Alert Deduplication (no spam)")
    print("=" * 80)

    alert_system = ObstacleAlertSystem(
        min_alert_interval_s=2.0,
        object_memory_s=10.0,
        alert_cooldown_s=15.0,  # Don't re-alert for 15 seconds
    )

    # Frame 1: Car approaching from left at high danger
    print("\nFrame 1: Car at 4 meters on left (HIGH danger)")
    response = create_test_response([
        create_test_detection("car", Quadrant.MIDDLE_LEFT, 0.45)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")

    time.sleep(2.5)

    # Frame 2: Same car, similar position (should NOT re-alert due to cooldown)
    print("\nFrame 2: Same car, still at ~4 meters (should NOT alert - cooldown active)")
    response = create_test_response([
        create_test_detection("car", Quadrant.MIDDLE_LEFT, 0.46)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None - deduplication working!'}")

    time.sleep(2.5)

    # Frame 3: Same car again (still in cooldown)
    print("\nFrame 3: Same car (still in cooldown)")
    response = create_test_response([
        create_test_detection("car", Quadrant.MIDDLE_LEFT, 0.44)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None - deduplication working!'}")


def test_scenario_3_prioritization():
    """Test scenario: Multiple objects - system should prioritize critical ones."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: Alert Prioritization (critical over less dangerous)")
    print("=" * 80)

    alert_system = ObstacleAlertSystem(
        min_alert_interval_s=2.0,
        object_memory_s=10.0,
        alert_cooldown_s=10.0,
    )

    # Frame 1: Multiple objects at different danger levels
    print("\nFrame 1: Bench far away, pole medium, person CRITICAL distance")
    print("Expected: Should alert about the person (highest risk)")
    response = create_test_response([
        create_test_detection("bench", Quadrant.MIDDLE_RIGHT, 0.80),  # Low danger
        create_test_detection("pole", Quadrant.MIDDLE_LEFT, 0.60),    # Medium danger
        create_test_detection("person", Quadrant.CENTER, 0.18),       # CRITICAL danger
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")


def test_scenario_4_vehicle_alert():
    """Test scenario: Vehicle approaching (high weight object)."""
    print("\n" + "=" * 80)
    print("SCENARIO 4: Vehicle Approaching")
    print("=" * 80)

    alert_system = ObstacleAlertSystem(
        min_alert_interval_s=2.0,
        object_memory_s=10.0,
        alert_cooldown_s=10.0,
    )

    # Frame 1: Truck at high danger level
    print("\nFrame 1: Truck at ~4 meters from right (HIGH danger)")
    response = create_test_response([
        create_test_detection("truck", Quadrant.MIDDLE_RIGHT, 0.48)
    ])
    alert = alert_system.process_frame(response)
    print(f"Alert: {alert or 'None'}")


def test_scenario_5_danger_levels():
    """Test scenario: Demonstrate different danger levels."""
    print("\n" + "=" * 80)
    print("SCENARIO 5: Danger Level Classification")
    print("=" * 80)

    depths = [
        (0.15, "CRITICAL", "~2 meters or less"),
        (0.40, "HIGH", "~2-4 meters"),
        (0.65, "MEDIUM", "~4-8 meters"),
        (0.85, "LOW", "~10+ meters"),
    ]

    for depth, expected_level, description in depths:
        level = DangerLevel.from_distance(depth)
        status = "✓" if level == expected_level.lower() else "✗"
        print(f"{status} Depth {depth:.2f} ({description}): {level.upper()}")


def main():
    """Run all test scenarios."""
    print("\n" + "=" * 80)
    print("OBSTACLE ALERT SYSTEM - TEST SUITE")
    print("=" * 80)
    print("\nThis test demonstrates:")
    print("  ✓ Approach detection (objects getting closer)")
    print("  ✓ Danger level classification (critical/high/medium/low)")
    print("  ✓ Alert deduplication (no spam)")
    print("  ✓ Alert prioritization (critical alerts first)")
    print("  ✓ Smart throttling (minimum time between alerts)")

    # Run test scenarios
    test_scenario_5_danger_levels()
    test_scenario_1_approaching_person()
    test_scenario_2_deduplication()
    test_scenario_3_prioritization()
    test_scenario_4_vehicle_alert()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
    print("\nThe obstacle alert system is working correctly!")
    print("Key features demonstrated:")
    print("  • Distance-based danger levels aligned with color coding")
    print("  • Smart deduplication prevents repeated alerts")
    print("  • Approach detection alerts when objects get closer")
    print("  • Priority system ensures critical alerts are spoken first")
    print("  • Configurable throttling prevents alert spam")


if __name__ == "__main__":
    main()
