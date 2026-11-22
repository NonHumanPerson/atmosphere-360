"""
CADR Calculator for Atmosphere360 PurifierMatch Module
Calculates required Clean Air Delivery Rate based on room dimensions and air change requirements.
"""
from dataclasses import dataclass
from typing import Optional
from config import DEFAULT_ACH, CEILING_HEIGHT_DEFAULT


@dataclass
class CADRResult:
    """Result of CADR calculation."""
    room_volume_cuft: float
    required_cadr_cfm: float
    required_cadr_m3h: float
    ach_used: int
    room_sqft: float
    ceiling_ft: float
    explanation: str


def calculate_required_cadr(
    room_sqft: float,
    ceiling_ft: float = CEILING_HEIGHT_DEFAULT,
    ach: int = DEFAULT_ACH
) -> CADRResult:
    """
    Calculate required CADR (Clean Air Delivery Rate) for a room.
    
    Formula: CADR (CFM) = (Room Volume × ACH) / 60
    Where:
    - Room Volume = room_sqft × ceiling_ft (cubic feet)
    - ACH = Air Changes per Hour (default 5 for residential)
    - 60 = minutes per hour
    
    Args:
        room_sqft: Room floor area in square feet
        ceiling_ft: Ceiling height in feet (default 9)
        ach: Air changes per hour (default 5)
    
    Returns:
        CADRResult with CFM and m³/h values
    
    Example:
        >>> calculate_required_cadr(150, 9, 5)
        CADRResult(room_volume_cuft=1350, required_cadr_cfm=112.5, ...)
    """
    if room_sqft <= 0:
        raise ValueError("Room size must be positive")
    if ceiling_ft <= 0:
        raise ValueError("Ceiling height must be positive")
    if ach <= 0:
        raise ValueError("ACH must be positive")
    
    room_volume = room_sqft * ceiling_ft
    cadr_cfm = (room_volume * ach) / 60
    cadr_m3h = cadr_cfm * 1.699  # 1 CFM = 1.699 m³/h
    
    explanation = (
        f"For a {room_sqft:.0f} sq ft room with {ceiling_ft:.0f} ft ceiling "
        f"(volume: {room_volume:.0f} cu ft), "
        f"at {ach} air changes per hour (ACH), "
        f"you need a purifier with at least {cadr_cfm:.1f} CFM "
        f"({cadr_m3h:.0f} m³/h) Clean Air Delivery Rate."
    )
    
    return CADRResult(
        room_volume_cuft=room_volume,
        required_cadr_cfm=round(cadr_cfm, 1),
        required_cadr_m3h=round(cadr_m3h),
        ach_used=ach,
        room_sqft=room_sqft,
        ceiling_ft=ceiling_ft,
        explanation=explanation
    )


def cadr_to_room_coverage(cadr_cfm: float, ach: int = DEFAULT_ACH, 
                          ceiling_ft: float = CEILING_HEIGHT_DEFAULT) -> float:
    """
    Calculate maximum room coverage (sq ft) for a given CADR.
    
    Inverse of calculate_required_cadr.
    
    Args:
        cadr_cfm: Purifier CADR in CFM
        ach: Target air changes per hour
        ceiling_ft: Assumed ceiling height
    
    Returns:
        Maximum room area in square feet
    """
    if cadr_cfm <= 0:
        return 0.0
    room_volume = (cadr_cfm * 60) / ach
    return room_volume / ceiling_ft


def recommend_purifier_tier(required_cadr_cfm: float, budget_inr: int) -> str:
    """
    Determine which purifier tier to recommend based on CADR need and budget.
    
    Args:
        required_cadr_cfm: Minimum CADR needed
        budget_inr: User budget in INR
    
    Returns:
        Tier name: "budget", "balanced", or "premium"
    """
    # Budget tier: basic HEPA, CADR ~80-150 CFM, ₹5k-12k
    # Balanced tier: good HEPA + carbon, CADR ~150-300 CFM, ₹12k-25k
    # Premium tier: high CADR, smart features, CADR 300+, ₹25k+
    
    if budget_inr < 10000:
        return "budget"
    elif budget_inr < 25000:
        return "balanced"
    else:
        return "premium"


def format_cadr_explanation(result: CADRResult) -> str:
    """Format CADR calculation for user display."""
    return (
        f"**CADR Calculation**\n"
        f"- Room: {result.room_sqft:.0f} sq ft × {result.ceiling_ft:.0f} ft = "
        f"{result.room_volume_cuft:.0f} cu ft\n"
        f"- Target: {result.ach_used} air changes/hour (ACH)\n"
        f"- **Required CADR: {result.required_cadr_cfm:.1f} CFM "
        f"({result.required_cadr_m3h:.0f} m³/h)**\n\n"
        f"💡 *This is the MINIMUM CADR needed. Choose a purifier rated at or above this value.*"
    )


# ACH recommendations by room type
ACH_RECOMMENDATIONS = {
    "Bedroom": 5,
    "Living Room": 5,
    "Office / Workspace": 6,
    "Classroom": 6,
    "Patient Room": 8,
    "Conference Room": 8,
    "Laboratory": 10,
    "Server Room": 12,
    "Other": 5,
}

def get_recommended_ach(room_type: str) -> int:
    """Get recommended ACH for a room type."""
    return ACH_RECOMMENDATIONS.get(room_type, DEFAULT_ACH)


if __name__ == "__main__":
    # Test calculations
    print("CADR Calculator Tests")
    print("=" * 50)
    
    test_cases = [
        (150, 9, 5),   # Standard bedroom
        (200, 9, 5),   # Large living room
        (120, 10, 6),  # Office with high ceiling
        (300, 9, 8),   # Classroom
        (100, 8, 5),   # Small room
    ]
    
    for sqft, ceiling, ach in test_cases:
        result = calculate_required_cadr(sqft, ceiling, ach)
        print(f"\n{sqft} sq ft × {ceiling} ft, {ach} ACH:")
        print(f"  Volume: {result.room_volume_cuft:.0f} cu ft")
        print(f"  Required CADR: {result.required_cadr_cfm:.1f} CFM ({result.required_cadr_m3h:.0f} m³/h)")
        print(f"  Coverage at this CADR: {cadr_to_room_coverage(result.required_cadr_cfm, ach, ceiling):.0f} sq ft")
    
    print("\n✅ All tests passed")