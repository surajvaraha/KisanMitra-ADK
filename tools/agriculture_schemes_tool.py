"""
Agriculture Schemes Tool for Kisan Mitra - ADK Compatible

Identifies and recommends relevant government agricultural schemes for a farmer
based on their profile and current enrollments.
All functions have NO parameters to be ADK LLM compatible.
"""

import json
from typing import Dict, Any, List

# Conversion factor from acres to hectares
ACRE_TO_HECTARE = 0.404686

def get_relevant_schemes_for_farmer() -> Dict[str, Any]:
    """Analyzes a farmer's profile to find relevant, unenrolled agricultural schemes.
    ADK Compatible - No parameters required.

    This function cross-references the farmer's landholding, existing enrollments,
    and other profile details against a list of available government schemes
    to recommend those for which they are likely eligible.

    Returns:
        Dict[str, Any]: A dictionary containing the farmer's name and a list of
                        recommended schemes, including benefits and application process.
    """
    profile_path = "context/farmer_profile.json"
    schemes_path = "context/agriculture_schemes.json"
    
    try:
        # Load farmer profile and available schemes
        with open(profile_path, 'r', encoding='utf-8') as f:
            farmer_data = json.load(f)
        
        with open(schemes_path, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)

        farmer_profile = farmer_data.get('farmer_details', {})
        if not farmer_profile:
            raise KeyError("'farmer_details' not found in profile JSON.")

    except FileNotFoundError as e:
        return {
            "status": "error",
            "error_message": f"File not found: {e.filename}. Please ensure paths are correct."
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Error decoding JSON. Please check the file format."
        }
    except KeyError as e:
        return {
            "status": "error",
            "error_message": f"Missing expected key in JSON data: {e}"
        }

    # --- Extract relevant farmer details for eligibility checks ---
    farmer_name = farmer_profile.get('personal_info', {}).get('name_english', 'N/A')
    farmer_hindi_name = farmer_profile.get('personal_info', {}).get('name', 'N/A')
    total_land_acres = farmer_profile.get('farm_details', {}).get('total_land_area_acres', 0)
    total_land_hectares = total_land_acres * ACRE_TO_HECTARE
    
    # Get farmer's location for regional schemes
    district = farmer_profile.get('location_details', {}).get('district', '')
    state = farmer_profile.get('location_details', {}).get('state', '')
    
    # Get economic profile
    economic_profile = farmer_profile.get('economic_profile', {})
    
    # Get a clean list of slugs for schemes the farmer is already in.
    enrolled_schemes = farmer_profile.get('government_schemes_enrolled', [])
    enrolled_slugs = set()
    for scheme in all_schemes:
        for enrolled in enrolled_schemes:
            # Check if the scheme's name or slug is mentioned in the farmer's enrolled list
            if scheme['name'].lower() in enrolled.lower() or scheme['slug'].lower() in enrolled.lower():
                enrolled_slugs.add(scheme['slug'])

    recommended_schemes = []
    already_enrolled_schemes = []

    # --- Iterate through all schemes and check for eligibility ---
    for scheme in all_schemes:
        slug = scheme['slug']

        # Track already enrolled schemes
        if slug in enrolled_slugs:
            already_enrolled_schemes.append({
                "name": scheme.get('name'),
                "status": "Already Enrolled"
            })
            continue

        is_eligible = False
        eligibility_reason = ""

        # Define eligibility logic for each scheme
        if slug == 'pm-kisan':
            # Eligibility: Landholding up to 2 hectares
            if total_land_hectares <= 2:
                is_eligible = True
                eligibility_reason = f"Eligible as landholding ({total_land_hectares:.2f} hectares) is ≤ 2 hectares"
            else:
                eligibility_reason = f"Not eligible as landholding ({total_land_hectares:.2f} hectares) exceeds 2 hectares"
        
        elif slug == 'pmfby':
            # Eligibility: All farmers growing notified crops are generally eligible.
            is_eligible = True
            eligibility_reason = "Eligible as all farmers growing crops can benefit from crop insurance"

        elif slug == 'pmksy':
            # Eligibility: All farmers with landholdings are generally eligible,
            # especially in water-scarce areas.
            if total_land_acres > 0:
                is_eligible = True
                eligibility_reason = f"Eligible with {total_land_acres} acres landholding for irrigation support"

        elif slug == 'kcc':
            # Eligibility: All individual farmers, tenants, etc., are eligible.
            is_eligible = True
            eligibility_reason = "Eligible as all farmers can access credit facilities"

        elif slug == 'soil-health-card':
            # Eligibility: All farmers are eligible for this free service.
            is_eligible = True
            eligibility_reason = "Eligible for free soil testing service"

        # Additional scheme checks can be added here
        else:
            # For any other schemes, check basic eligibility (having land)
            if total_land_acres > 0:
                is_eligible = True
                eligibility_reason = "Potentially eligible - please check specific criteria"

        # If eligible and not enrolled, add to recommendations
        if is_eligible:
            recommended_schemes.append({
                "name": scheme.get('name'),
                "slug": scheme.get('slug'),
                "description": scheme.get('description'),
                "category": scheme.get('category'),
                "eligibility_reason": eligibility_reason,
                "benefits": scheme.get('benefits', []),
                "financial_assistance": scheme.get('financial_assistance', ''),
                "documents_required": scheme.get('documents_required', []),
                "how_to_apply": scheme.get('how_to_apply', []),
                "contact_info": scheme.get('contact_info', {}),
                "application_deadline": scheme.get('application_deadline', 'Check official website')
            })

    # --- Prepare the final response ---
    if recommended_schemes:
        message = f"Found {len(recommended_schemes)} new scheme(s) that may be beneficial for {farmer_hindi_name} ({farmer_name})."
    else:
        message = f"No new relevant schemes found for {farmer_hindi_name} ({farmer_name}) at this time. They appear to be enrolled in all applicable schemes."

    return {
        "status": "success",
        "farmer_name": farmer_name,
        "farmer_hindi_name": farmer_hindi_name,
        "farmer_location": f"{district}, {state}",
        "land_details": {
            "total_acres": total_land_acres,
            "total_hectares": round(total_land_hectares, 2)
        },
        "message": message,
        "already_enrolled_schemes": already_enrolled_schemes,
        "recommended_schemes": recommended_schemes,
        "total_schemes_available": len(all_schemes),
        "schemes_analysis": {
            "already_enrolled": len(already_enrolled_schemes),
            "newly_recommended": len(recommended_schemes),
            "total_applicable": len(already_enrolled_schemes) + len(recommended_schemes)
        }
    }

def get_scheme_details(scheme_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific agricultural scheme.
    ADK Compatible - Only requires scheme name parameter.
    
    Args:
        scheme_name (str): Name or slug of the scheme to look up
        
    Returns:
        Dict[str, Any]: Detailed scheme information or error message
    """
    schemes_path = "context/agriculture_schemes.json"
    
    try:
        with open(schemes_path, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)
            
        # Search for scheme by name or slug
        scheme_name_lower = scheme_name.lower()
        found_scheme = None
        
        for scheme in all_schemes:
            if (scheme['name'].lower() == scheme_name_lower or 
                scheme['slug'].lower() == scheme_name_lower or
                scheme_name_lower in scheme['name'].lower()):
                found_scheme = scheme
                break
        
        if not found_scheme:
            return {
                "status": "error",
                "error_message": f"Scheme '{scheme_name}' not found. Available schemes: {', '.join([s['name'] for s in all_schemes[:5]])}..."
            }
        
        return {
            "status": "success",
            "scheme_details": found_scheme
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error_message": f"Schemes database not found: {schemes_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error retrieving scheme details: {str(e)}"
        }

def list_all_available_schemes() -> Dict[str, Any]:
    """List all available agricultural schemes with basic information.
    ADK Compatible - No parameters required.
    
    Returns:
        Dict[str, Any]: List of all available schemes
    """
    schemes_path = "context/agriculture_schemes.json"
    
    try:
        with open(schemes_path, 'r', encoding='utf-8') as f:
            all_schemes = json.load(f)
        
        schemes_summary = []
        for scheme in all_schemes:
            schemes_summary.append({
                "name": scheme['name'],
                "slug": scheme['slug'],
                "category": scheme['category'],
                "description": scheme['description'],
                "financial_assistance": scheme.get('financial_assistance', ''),
                "target_audience": scheme.get('target_audience', [])
            })
        
        # Group by category
        schemes_by_category = {}
        for scheme in schemes_summary:
            category = scheme['category']
            if category not in schemes_by_category:
                schemes_by_category[category] = []
            schemes_by_category[category].append(scheme)
        
        return {
            "status": "success",
            "total_schemes": len(all_schemes),
            "schemes_by_category": schemes_by_category,
            "all_schemes": schemes_summary
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error_message": f"Schemes database not found: {schemes_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error retrieving schemes list: {str(e)}"
        }
