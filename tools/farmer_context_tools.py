"""
Farmer Context Tools for Enhanced Multilingual Agronomist - ADK Compatible

Provides farmer profile context and personalized agricultural insights.
All functions have NO parameters to be ADK LLM compatible.
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

def load_farmer_profile() -> Dict[str, Any]:
    """Load farmer profile from the default JSON file location.
    ADK Compatible - No parameters required.
    
    Returns:
        Dict[str, Any]: Farmer profile data or error message
    """
    profile_path = "context/farmer_profile.json"
    
    try:
        if not os.path.exists(profile_path):
            return {
                "status": "error",
                "error_message": f"Farmer profile file not found: {profile_path}. Please create farmer profile first."
            }
        
        with open(profile_path, 'r', encoding='utf-8') as file:
            profile_data = json.load(file)
            
        # Validate required fields
        required_fields = ['farmer_details']
        if not all(field in profile_data for field in required_fields):
            return {
                "status": "error",
                "error_message": "Invalid farmer profile format. Missing required fields."
            }
            
        return {
            "status": "success",
            "farmer_profile": profile_data['farmer_details'],
            "context_instructions": profile_data.get('context_usage_instructions', {}),
            "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error_message": f"Invalid JSON format in farmer profile: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error loading farmer profile: {str(e)}"
        }

def get_farmer_context_summary() -> Dict[str, Any]:
    """Get a summarized farmer context for quick reference.
    ADK Compatible - No parameters required.
    Automatically loads from the default farmer profile location.
    
    Returns:
        Dict[str, Any]: Summarized farmer context with language preference
    """
    profile_result = load_farmer_profile()
    
    if profile_result["status"] == "error":
        return profile_result
    
    farmer = profile_result["farmer_profile"]
    
    # Extract key context information
    summary = {
        "status": "success",
        "farmer_summary": {
            "name": farmer["personal_info"]["name"],
            "name_english": farmer["personal_info"]["name_english"],
            "location": {
                "village": farmer["location_details"]["village"],
                "district": farmer["location_details"]["district"],
                "state": farmer["location_details"]["state"],
                "agro_climatic_zone": farmer["location_details"]["agro_climatic_zone"]
            },
            "primary_language": farmer["personal_info"]["primary_language"],
            "farm_size_acres": farmer["farm_details"]["total_land_area_acres"],
            "current_crops": []
        },
        "quick_context": {
            "soil_types": [soil["type"] for soil in farmer["farm_details"]["soil_types"]],
            "irrigation_sources": [source["type"] for source in farmer["farm_details"]["water_sources"]],
            "major_challenges": farmer["challenges_faced"][:3],  # Top 3 challenges
            "preferred_communication": {
                "language": farmer["personal_info"]["primary_language"],
                "timing": farmer["preferences"]["advisory_timing"],
                "format": farmer["preferences"]["information_format"]
            }
        }
    }
    
    # Add current crop information
    if "kharif_crops" in farmer["cropping_pattern"]:
        for crop in farmer["cropping_pattern"]["kharif_crops"]:
            summary["farmer_summary"]["current_crops"].append({
                "crop": crop["crop_name"],
                "variety": crop["variety"],
                "area_acres": crop["area_acres"],
                "growth_stage": crop["growth_stage"],
                "sowing_date": crop["sowing_date"]
            })
    
    return summary

def get_crop_specific_context(crop_name: str) -> Dict[str, Any]:
    """Get crop-specific context from farmer profile for a given crop.
    
    Args:
        crop_name (str): Name of the crop to get context for
        
    Returns:
        Dict[str, Any]: Crop-specific context and recommendations
    """
    profile_result = load_farmer_profile()
    
    if profile_result["status"] == "error":
        return profile_result
    
    farmer = profile_result["farmer_profile"]
    crop_context = None
    
    # Search in current kharif crops
    for crop in farmer["cropping_pattern"].get("kharif_crops", []):
        if crop["crop_name"].lower() == crop_name.lower():
            crop_context = crop
            season = "kharif"
            break
    
    # Search in planned rabi crops
    if not crop_context:
        for crop in farmer["cropping_pattern"].get("rabi_crops_planned", []):
            if crop["crop_name"].lower() == crop_name.lower():
                crop_context = crop
                season = "rabi_planned"
                break
    
    if not crop_context:
        return {
            "status": "error",
            "error_message": f"Crop '{crop_name}' not found in farmer's current or planned cropping pattern."
        }
    
    # Calculate days since sowing (for current crops)
    days_since_sowing = None
    if "sowing_date" in crop_context:
        try:
            sowing_date = datetime.strptime(crop_context["sowing_date"], "%Y-%m-%d")
            days_since_sowing = (datetime.now() - sowing_date).days
        except:
            pass
    
    # Get relevant soil information for the crop area
    relevant_soil = None
    if crop_context.get("area_acres"):
        for soil in farmer["farm_details"]["soil_types"]:
            if soil["area_acres"] >= crop_context["area_acres"]:
                relevant_soil = soil
                break
    
    return {
        "status": "success",
        "crop_context": {
            "crop_details": crop_context,
            "season": season,
            "days_since_sowing": days_since_sowing,
            "farmer_location": {
                "district": farmer["location_details"]["district"],
                "state": farmer["location_details"]["state"],
                "agro_climatic_zone": farmer["location_details"]["agro_climatic_zone"],
                "coordinates": farmer["location_details"]["coordinates"]
            },
            "soil_context": relevant_soil,
            "irrigation_available": farmer["farm_details"]["irrigated_area_acres"] > 0,
            "farmer_experience": {
                "previous_yield": crop_context.get("previous_yield_tons_per_acre"),
                "seed_source": crop_context.get("seed_source"),
                "irrigation_method": crop_context.get("irrigation_method")
            },
            "input_patterns": {
                "fertilizer_usage": farmer["input_usage"]["fertilizers"],
                "pesticide_usage": farmer["input_usage"]["pesticides"],
                "organic_practices": farmer["input_usage"]["fertilizers"]["organic_manure_tons_per_acre"] > 0
            },
            "economic_context": {
                "investment_capacity": farmer["economic_profile"]["investment_capacity"]["annual_input_budget_inr"],
                "market_access": farmer["economic_profile"]["market_linkages"]["primary_buyer"],
                "insurance_coverage": farmer["economic_profile"]["investment_capacity"]["insurance_coverage"]
            }
        }
    }

def get_seasonal_recommendations() -> Dict[str, Any]:
    """Get season-specific recommendations based on farmer profile and current date.
    ADK Compatible - No parameters required.
    
    Returns:
        Dict[str, Any]: Seasonal recommendations
    """
    profile_result = load_farmer_profile()
    
    if profile_result["status"] == "error":
        return profile_result
    
    farmer = profile_result["farmer_profile"]
    current_date = datetime.now()
    current_month = current_date.month
    
    # Determine current season
    if current_month in [6, 7, 8, 9, 10]:
        season = "kharif"
        season_stage = "active"
    elif current_month in [11, 12, 1, 2, 3]:
        season = "rabi"
        season_stage = "active"
    else:  # April, May
        season = "summer"
        season_stage = "preparation"
    
    recommendations = {
        "status": "success",
        "seasonal_recommendations": {
            "current_season": season,
            "season_stage": season_stage,
            "month": current_month,
            "location": farmer["location_details"]["district"],
            "priority_actions": [],
            "crop_care_tips": [],
            "input_recommendations": [],
            "weather_considerations": []
        }
    }
    
    # Season-specific recommendations
    if season == "kharif":
        recommendations["seasonal_recommendations"]["priority_actions"] = [
            "Monitor pest activity - especially stem borer in rice",
            "Ensure proper drainage during heavy rains",
            "Apply second dose of nitrogen fertilizer",
            "Check for disease symptoms in humid conditions"
        ]
        
        # Current crop specific tips
        for crop in farmer["cropping_pattern"].get("kharif_crops", []):
            if crop["crop_name"].lower() == "rice":
                recommendations["seasonal_recommendations"]["crop_care_tips"].append(
                    f"Rice in {crop['growth_stage']} stage - monitor for blast disease"
                )
            elif crop["crop_name"].lower() == "sugarcane":
                recommendations["seasonal_recommendations"]["crop_care_tips"].append(
                    f"Sugarcane in {crop['growth_stage']} stage - ensure adequate water and earthing up"
                )
    
    elif season == "rabi":
        recommendations["seasonal_recommendations"]["priority_actions"] = [
            "Prepare for wheat sowing if not done",
            "Monitor for aphid infestation in mustard",
            "Arrange irrigation schedule for winter crops",
            "Apply potash fertilizer for root development"
        ]
        
        # Planned crop preparations
        for crop in farmer["cropping_pattern"].get("rabi_crops_planned", []):
            recommendations["seasonal_recommendations"]["crop_care_tips"].append(
                f"Prepare for {crop['crop_name']} sowing - arrange {crop['seed_requirement_kg']}kg seeds"
            )
    
    # Add location-specific considerations
    state = farmer["location_details"]["state"]
    if state.lower() in ["uttar pradesh", "punjab", "haryana"]:
        if season == "kharif":
            recommendations["seasonal_recommendations"]["weather_considerations"].append(
                "Monitor for excessive rainfall and waterlogging in Indo-Gangetic plains"
            )
        elif season == "rabi":
            recommendations["seasonal_recommendations"]["weather_considerations"].append(
                "Prepare for possible fog and cold wave affecting wheat growth"
            )
    
    return recommendations 