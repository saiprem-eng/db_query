import streamlit as st
import requests
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="10D Stores - AI Database Action Analyzer",
    page_icon="🏪",
    layout="wide"
)

# --- API Call Function ---
def analyze_action_with_ai(user_query: str):
    """
    Calls the Gemini API to analyze the user's action against the DB schema.
    """
    # For deployment, it's crucial to use st.secrets for your API key
    api_key = st.secrets.get("GEMINI_API_KEY", "") 
    if not api_key:
        st.error("GEMINI_API_KEY is not set in Streamlit secrets. The app cannot function without it. Please add it to your .streamlit/secrets.toml file.", icon="🚨")
        return None

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

    db_schema = """
        10D Stores Firestore Database Schema:
        
        1. users (Document ID: userId)
           - uid, email, displayName, photoUrl, userType, phoneNumber, isPhoneVerified
           - createdAt, lastLoginAt, fcmTokens, isActive, favoritedBusinessIds
        
        2. businesses (Document ID: auto-generated)
           - businessId, ownerId, businessName, description, logoUrl, coverImages
           - category, contactInfo (phone, email), address (street, city, state, zipCode)
           - geolocation, uniqueQrCodeId, verificationStatus, verificationDocs
           - adminNotes, createdAt, lastUpdatedAt, isSuspended, suspensionReason
        
        3. business_public_profiles (Document ID: businessId)
           - businessId, businessName, logoUrl, category, city, geolocation
           - averageRating, reviewCount, activeOfferCount
        
        4. products (Document ID: auto-generated)
           - productId, businessId, name, description, imageUrl, price
           - productCategory, marginType, isActive, createdAt, lastUpdatedAt
        
        5. offers (Document ID: auto-generated)
           - offerId, businessId, businessName, title, description
           - discountType, discountValue, status, applicability (scope, targetProductIds, targetProductCategories, targetMarginTypes)
           - conditions (minBillAmount, validFrom, validUntil, applicableDays, time)
           - usageLimits (limitPerUser, totalLimit), usageStats (timesUsed)
           - createdBy, createdAt
        
        6. redemptions (Document ID: auto-generated)
           - redemptionId, userId, businessId, offerId, timestamp
           - billDetails (amountBeforeDiscount, calculatedDiscount, amountAfterDiscount)
           - offerSnapshot (title, discountType, discountValue)
           - userDisplayName, businessName
        
        7. reviews (Document ID: auto-generated)
           - reviewId, businessId, userId, redemptionId, rating, reviewText
           - timestamp, ownerResponseText, ownerResponseTimestamp
           - isHiddenByAdmin, moderationNotes
        
        8. platform_config (Document ID: "global_settings")
           - businessCategories, minRequiredAppVersionCustomer, minRequiredAppVersionBusiness
           - isForceUpdateRequired, maintenanceMode, supportContact
           - termsAndConditionsUrl, privacyPolicyUrl
    """

    system_prompt = """
        You are an expert Firestore database analyst for the 10D Stores application. Your task is to analyze a user-described action and determine its impact on the provided Firestore collections.
        
        The 10D Stores app is a discount/offer platform where:
        - Users can browse businesses, view offers, redeem discounts, and leave reviews
        - Business owners can create offers and manage their business profiles
        - The system tracks redemptions, reviews, and user preferences
        
        You MUST respond with ONLY a valid JSON object following this exact structure. Do not include markdown, comments, or any other text.
        {
          "description": "A detailed paragraph summarizing the Firestore operations. Explain what data is being read for validation or context, and what new data is being written or which fields are being updated. Be specific about the flow of operations and how it relates to the 10D Stores business logic. IMPORTANT: When you mention a field name from the schema, you MUST wrap it in double asterisks. For example: '...checks the **isActive** field...' or '...updates the **favoritedBusinessIds** array...'.",
          "impact": [
            {
              "table": "CollectionName",
              "operation": "READ" | "WRITE" | "DELETE",
              "fields": ["field1", "field2"],
              "reason": "A concise explanation of why this operation occurs in the context of 10D Stores."
            }
          ]
        }
    """

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
        }
    }

    try:
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        result = response.json()
        
        json_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not json_text:
            raise ValueError("Received an empty or invalid response from the AI.")
            
        return json.loads(json_text)
    except requests.exceptions.RequestException as e:
        st.error(f"Network error calling the API: {e}")
    except (ValueError, KeyError, IndexError) as e:
        st.error(f"Error parsing the API response: {e}. The AI might have returned an unexpected format.")
        st.json(result if 'result' in locals() else "No response object available.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        
    return None

# --- UI Helper Functions ---
def get_operation_badge(operation):
    """Generates an HTML badge for the operation type."""
    op = operation.upper()
    colors = {
        "READ": ("#e0f2fe", "#0284c7"),    # Tailwind sky-100, sky-600
        "WRITE": ("#d1fae5", "#059669"),   # Tailwind emerald-100, emerald-600
        "DELETE": ("#fee2e2", "#dc2626"),  # Tailwind red-100, red-600
    }
    bg_color, text_color = colors.get(op, ("#e5e7eb", "#4b5563")) # gray-200, gray-600
    
    return f'<span style="background-color: {bg_color}; color: {text_color}; font-size: 0.75rem; font-weight: 600; padding: 4px 8px; border-radius: 9999px; float: right;">{op}</span>'

# --- Main App Interface ---
st.title("🏪 10D Stores - AI Database Action Analyzer")
st.markdown("Describe any user action related to the 10D Stores app, and the AI will analyze its impact on the Firestore database schema.")

st.markdown("---")

# Input section
action_input = st.text_area(
    "**Describe the User Action**",
    placeholder="e.g., A customer redeems a 20% off offer at a restaurant, A business owner creates a new discount offer, A user leaves a review after redeeming an offer",
    height=100,
    key="action_input"
)

analyze_button = st.button("Analyze Action", type="primary", use_container_width=True)

# Results section
if analyze_button and action_input:
    with st.spinner("Analyzing your action... This may take a moment."):
        analysis_result = analyze_action_with_ai(action_input)
    
    if analysis_result:
        st.markdown("---")
        st.header(f'Analysis for: "{action_input}"', divider='rainbow')
        
        # The description from the AI already uses markdown for bolding (**field**), 
        # so Streamlit's st.markdown can render it directly.
        st.markdown(analysis_result.get("description", "No description provided."))

        st.subheader("Affected Collections & Fields")
        
        impacts = analysis_result.get("impact", [])
        if not impacts:
            st.info("The AI determined this action has no direct impact on the database.")
        else:
            for item in impacts:
                with st.container(border=True):
                    st.markdown(f'<h4>{item.get("table", "N/A")} {get_operation_badge(item.get("operation", "N/A"))}</h4>', unsafe_allow_html=True)
                    st.caption(item.get("reason", "No reason provided."))
                    
                    fields = item.get("fields", [])
                    if fields:
                        # Display fields as styled tags using HTML in markdown
                        fields_html = "".join([f'<span style="background-color: #f3f4f6; color: #1f2937; font-family: monospace; font-size: 0.875rem; padding: 2px 6px; border-radius: 4px; margin: 2px 4px 2px 0;">{field}</span>' for field in fields])
                        st.markdown(fields_html, unsafe_allow_html=True)
                    
elif not st.session_state.get("action_input"):
    st.info("Enter an action above and click 'Analyze' to see the results.")
