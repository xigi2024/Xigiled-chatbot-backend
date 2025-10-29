# Alexa/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import ChatLog, ChatSession, ChatMessage
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import re
import uuid

# ---------------------------
# In-memory session store (prototype)
# ---------------------------
SESSIONS = {}

# ---------------------------
# Step definitions for conversation flow
# ---------------------------


STEPS = {
    'greeting': {
        'next': 'application_purpose',
        'message': "Hello! Welcome to XIGI LED Assistant. Where will you use the LED panel? (e.g., Mall, Event Hall, Studio, Outdoor Stage, Church, Manufacturing Factory, Manufacturer)"
    },
    'application_purpose': {
        'next': 'panel_category',
        'message': "Based on your purpose, I recommend the following panel type. Please confirm or select from options."
    },
    'panel_category': {
        'next': 'panel_selection',
        'message': "Great! Please select a panel from the options below."
    },
    'panel_selection': {
        'next': 'size_input',
        'message': "Please enter your screen width and height in feet/meters (e.g., '10x6 ft')."
    },
    'size_input': {
        'next': 'quantity_input',
        'message': "How many panels do you need?"
    },
    'quantity_input': {
        'next': 'controller_inclusion',
        'message': "Would you like to include controller, cabinets, and mounting structure? (Yes/No)"
    },
    'controller_inclusion': {
        'next': 'installation',
        'message': "Do you need on-site installation support? (Yes/No)"
    },
    'installation': {
        'next': 'delivery_location',
        'message': "Please provide delivery location."
    },
    'delivery_location': {
        'next': 'client_info',
        'message': "Please provide your company name."
    },
    'client_info': {
        'next': 'review_confirmation',
        'message': "Please provide contact person name."
    },
    'contact_person': {
        'next': 'mobile_number',
        'message': "Please provide mobile number."
    },
    'mobile_number': {
        'next': 'email_address',
        'message': "Please provide email address."
    },
    'email_address': {
        'next': 'review_confirmation',
        'message': "All information collected. Would you like to review your configuration? (Yes/No)"
    },
    'review_confirmation': {
        'next': 'final_action',
        'message': "Would you like to save this configuration or modify something? (Save/Modify)"
    },
    'modify_options': {
        'next': 'review_confirmation',
        'message': "What would you like to modify? (size, quantity, delivery, purpose, panel, controller, installation, contact)"
    },
    'multiple_modifications': {
        'next': 'review_confirmation',
        'message': "Please provide the new values separated by commas."
    },
    'final_action': {
        'next': None,
        'message': "Configuration saved! Our team will contact you soon."
    }
}

# ---------------------------
# Panel Specs (INDOOR + OUTDOOR) - trimmed to what you provided
# ---------------------------
INDOOR_SPECS = {
    'P1.25mm': {
        'module_resolutions': ['256x128'],
        'led_types': ['SMD 3 in1'],
        'brightness_options': ['600-800'],
        'module_sizes': ['320x160'],
        'scan_times': ['1/64Scan'],
        'pixel_pitch': 'P1.25mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹250,000 – ₹320,000',
        'price_per_cabinet': '₹60,000 – ₹80,000'
    },
    'P2.5mm': {
        'module_resolutions': ['128x64'],
        'led_types': ['SMD 3 in1'],
        'brightness_options': ['800-1000'],
        'module_sizes': ['320x160'],
        'scan_times': ['1/32Scan'],
        'pixel_pitch': 'P2.5mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹95,000 – ₹125,000',
        'price_per_cabinet': '₹25,000 – ₹32,000'
    },
    'P3mm': {
        'module_resolutions': ['192x192'],
        'led_types': ['SMD 3 in1'],
        'brightness_options': ['900'],
        'module_sizes': ['320x160'],
        'scan_times': ['1/16Scan'],
        'pixel_pitch': 'P3mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹75,000 – ₹95,000',
        'price_per_cabinet': '₹20,000 – ₹25,000'
    },
    'P3.91mm': {
        'module_resolutions': ['64x64'],
        'led_types': ['SMD 3 in1'],
        'brightness_options': ['800-1000'],
        'module_sizes': ['250x250'],
        'scan_times': ['1/16Scan'],
        'pixel_pitch': 'P3.91mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹65,000 – ₹85,000',
        'price_per_cabinet': '₹18,000 – ₹22,000'
    },
    'P4.81mm': {
        'module_resolutions': ['52x52'],
        'led_types': ['SMD 3 in1'],
        'brightness_options': ['800-1000'],
        'module_sizes': ['250x250'],
        'scan_times': ['1/13Scan'],
        'pixel_pitch': 'P4.81mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹60,000 – ₹75,000',
        'price_per_cabinet': '₹16,000 – ₹20,000'
    },
    'P6mm': {
        'module_resolutions': ['32x16'],
        'led_types': ['White LED'],
        'brightness_options': ['800-1000'],
        'module_sizes': ['192x96'],
        'driving_modes': ['1/8Scan'],
        'pixel_pitch': 'P6mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹50,000 – ₹65,000',
        'price_per_cabinet': '₹14,000 – ₹17,000'
    },
    'P10mm': {
        'module_resolutions': ['32x16'],
        'led_types': ['White LED'],
        'brightness_options': ['800-1000'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/4Scan'],
        'pixel_pitch': 'P10mm',
        'ip_rating': 'IP30',
        'price_per_sq_meter': '₹40,000 – ₹55,000',
        'price_per_cabinet': '₹12,000 – ₹15,000'
    }
    # Add more indoor entries from your list as needed...
}

OUTDOOR_SPECS = {
    'P3.076mm': {
        'module_resolutions': ['104x52'],
        'led_types': ['SMD1415'],
        'brightness_options': ['>5000'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/13Scan'],
        'pixel_pitch': 'P3.076mm',
        'ip_rating': 'IP65'
    },
    'P4mm': {
        'module_resolutions': ['80x40'],
        'led_types': ['SMD1921'],
        'brightness_options': ['>5500'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/10Scan'],
        'pixel_pitch': 'P4mm',
        'ip_rating': 'IP67'
    },
    'P5mm': {
        'module_resolutions': ['64x32'],
        'led_types': ['SMD1921'],
        'brightness_options': ['>5200'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/8Scan'],
        'pixel_pitch': 'P5mm',
        'ip_rating': 'IP67',
        'price_per_sq_meter': '₹55,000 – ₹70,000',
        'price_per_cabinet': '₹15,000 – ₹18,000'
    },
    'P6.67mm': {
        'module_resolutions': ['48x24'],
        'led_types': ['SMD3535'],
        'brightness_options': ['>5500'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/6Scan'],
        'pixel_pitch': 'P6.67mm',
        'ip_rating': 'IP67',
        'price_per_sq_meter': '₹50,000 – ₹65,000',
        'price_per_cabinet': '₹14,000 – ₹17,000'
    },
    'P8mm': {
        'module_resolutions': ['40x20'],
        'led_types': ['SMD3535'],
        'brightness_options': ['>5800'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/5Scan'],
        'pixel_pitch': 'P8mm',
        'ip_rating': 'IP67'
    },
    'P10mm': {
        'module_resolutions': ['32x16'],
        'led_types': ['SMD3535'],
        'brightness_options': ['>6000'],
        'module_sizes': ['320x160'],
        'driving_modes': ['1/2Scan'],
        'pixel_pitch': 'P10mm',
        'ip_rating': 'IP67',
        'price_per_sq_meter': '₹40,000 – ₹55,000',
        'price_per_cabinet': '₹12,000 – ₹15,000'
    }
    # Add more outdoor entries if required...
}

# ---------------------------
# Accessory Recommendations
# ---------------------------
ACCESSORY_RECOMMENDATIONS = {
    'indoor': {
        'controllers': ['Novastar VX600', 'Colorlight X8', 'Linsn TS802D'],
        'power_supplies': ['200W Power Supply', '500W Power Supply'],
        'cables': ['HDMI Cables', 'Ethernet Cables'],
        'cabinets': ['Indoor Aluminum Cabinets', 'Steel Cabinets'],
        'mounting': ['Wall Mount Kits', 'Ceiling Mount Kits']
    },
    'outdoor': {
        'controllers': ['Novastar VX600', 'Colorlight X8', 'Linsn TS802D'],
        'power_supplies': ['500W Power Supply', '1000W Power Supply'],
        'cables': ['HDMI Cables', 'Ethernet Cables'],
        'weatherproofing': ['Protective Covers', 'Sealing Kits'],
        'cabinets': ['Outdoor Waterproof Cabinets', 'IP67 Rated Cabinets'],
        'mounting': ['Pole Mount Kits', 'Ground Mount Structures']
    }
}

PRODUCT_BUNDLES = {
    'indoor': {
        'essential': {
            'name': 'Essential Kit',
            'items': {
                'controller': 'Novastar VX600',
                'power_supply': '500W Power Supply',
                'cables': 'Ethernet + HDMI Cables',
                'mounting': 'Wall Mount Kit'
            }
        },
        'professional': {
            'name': 'Professional Kit',
            'items': {
                'controller': 'Colorlight X8',
                'power_supply': '1000W Power Supply',
                'cables': 'Ethernet + HDMI + Fiber Cables',
                'cabinet': 'Aluminum Cabinet',
                'mounting': 'Ceiling Mount Kit'
            }
        }
    },
    'outdoor': {
        'essential': {
            'name': 'Essential Kit',
            'items': {
                'controller': 'Novastar VX600',
                'power_supply': '1000W Power Supply',
                'cables': 'Weatherproof Ethernet + HDMI',
                'weatherproofing': 'Protective Cover',
                'mounting': 'Pole Mount Kit'
            }
        },
        'professional': {
            'name': 'Professional Kit',
            'items': {
                'controller': 'Colorlight X8',
                'power_supply': '2000W Power Supply',
                'cables': 'Weatherproof Cables + Fiber',
                'cabinet': 'IP67 Waterproof Cabinet',
                'weatherproofing': 'Complete Sealing Kit',
                'mounting': 'Ground Mount Structure'
            }
        }
    }
}

# Purpose-based recommendations
PURPOSE_RECOMMENDATIONS = {
    'event hall': {
        'tips': [
            'Ensure high brightness for large viewing distances (typically 5000+ nits).',
            'Consider modular panels for flexible configuration in different venues.',
            'Recommend controllers with hot-swapping capability for quick repairs.',
            'Consider rental vs. purchase based on frequency of use.'
        ],
        'additional_accessories': ['Truss Systems', 'Rigging Hardware', 'Quick-Release Mounting Brackets'],
        'panel_recommendation': 'Outdoor panels (P3-P5mm) for high brightness; Indoor P2.5-P3.91mm for auditorium setups',
        'estimated_brightness': 'Minimum 5000 nits for distance viewing',
        'setup_steps': [
            '1. Assess the venue layout and determine optimal screen placement for maximum visibility from all seating areas.',
            '2. Ensure power supply and cabling can handle the display load; consider backup generators for critical events.',
            '3. Test brightness and color accuracy in the actual lighting conditions of the hall.',
            '4. Coordinate with event staff for rigging, safety checks, and emergency evacuation routes.',
            '5. Perform a full system test, including failover scenarios, before the event starts.',
            '6. Monitor temperature and ventilation to prevent overheating during long events.'
        ]
    },
    'studio': {
        'tips': [
            'Prioritize color accuracy and low input latency for live broadcasts.',
            'Choose smaller pixel pitch for detailed content visibility.',
            'Consider background lighting vs. main display based on studio size.',
            'Plan for thermal management in enclosed spaces.'
        ],
        'additional_accessories': ['Color Calibration Tools', 'Green Screen Backdrops', 'LED Color Management Software'],
        'panel_recommendation': 'Indoor P1.25-P2.5mm for high definition and color accuracy',
        'estimated_brightness': '600-800 nits for controlled indoor lighting',
        'setup_steps': [
            '1. Position panels to avoid reflections and ensure even lighting across the studio.',
            '2. Calibrate color temperature to match studio lighting and camera settings.',
            '3. Integrate with broadcast equipment for low-latency signal transmission.',
            '4. Install in a controlled environment to maintain consistent performance.',
            '5. Test with actual broadcast scenarios, including live feeds and recordings.',
            '6. Implement cooling systems if panels will be used for extended periods.'
        ]
    },
    'mall': {
        'tips': [
            'High visibility and durability essential for 24/7 operation.',
            'Integrate with existing mall signage systems and digital networks.',
            'Plan for remote content management across multiple displays.',
            'Consider energy consumption for continuous operation.'
        ],
        'additional_accessories': ['Digital Signage Software', 'Content Management Systems', 'Network Integration Kits'],
        'panel_recommendation': 'Indoor P2.5-P4mm or Outdoor P4-P5mm depending on location (indoor vs. outdoor signage)',
        'estimated_brightness': 'Indoor: 800-1000 nits; Outdoor: 5000+ nits',
        'setup_steps': [
            '1. Choose locations with high foot traffic and minimal obstructions for optimal visibility.',
            '2. Ensure panels are securely mounted to withstand public interaction.',
            "3. Integrate with mall's central content management system for unified control.",
            '4. Schedule maintenance windows during low-traffic hours.',
            '5. Test display performance under varying crowd sizes and lighting conditions.',
            '6. Implement energy-saving modes for off-peak hours.'
        ]
    },
    'outdoor stage': {
        'tips': [
            'Weather-resistant and high brightness essential (6000+ nits for daylight).',
            'Consider wind and rain protection; ensure proper drainage.',
            'Plan for thermal dissipation in hot climates.',
            'Implement redundant power supplies for critical events.'
        ],
        'additional_accessories': ['Weatherproof Enclosures', 'Ground Stakes', 'Lightning Protection Kits', 'Thermal Management Systems'],
        'panel_recommendation': 'Outdoor panels P4-P6.67mm with IP67 or higher rating',
        'estimated_brightness': 'Minimum 6000 nits for outdoor daytime visibility',
        'setup_steps': [
            '1. Select weatherproof panels and enclosures suitable for the local climate.',
            '2. Secure panels against wind and vibration using appropriate mounting hardware.',
            '3. Position screens to avoid direct sunlight glare and ensure visibility from all audience areas.',
            '4. Install lightning protection and grounding systems.',
            '5. Test under simulated weather conditions and perform acoustic checks if near speakers.',
            '6. Have backup power and quick-replacement panels on site for large events.'
        ]
    },
    'church': {
        'tips': [
            'Subtle, warm lighting creates ambiance without distraction.',
            'Consider acoustic considerations and vibration isolation.',
            'Plan for gradual brightness adjustment during services.',
            'Integrate with audio systems for synchronized content.'
        ],
        'additional_accessories': ['Dimming Controllers', 'Sound Integration Kits', 'Subtle Color Temperature Controls'],
        'panel_recommendation': 'Indoor P3-P4mm with warm color temperature support',
        'estimated_brightness': '400-600 nits for comfortable viewing in dim environments',
        'setup_steps': [
            '1. Position displays to complement the worship space without dominating the environment.',
            '2. Use dimming controls to adjust brightness for different parts of the service.',
            '3. Ensure panels are mounted securely to avoid vibrations from music or movement.',
            '4. Integrate with sound systems for synchronized multimedia presentations.',
            '5. Test visibility from all seating areas, considering ambient lighting.',
            '6. Schedule installations during off-service times to minimize disruption.'
        ]
    },
    'temple': {
        'tips': [
            'Respect cultural sensitivities with subtle, reverent lighting.',
            'Consider acoustic and vibrational impacts in sacred spaces.',
            'Plan for adjustable brightness to accommodate various ceremonies.',
            'Ensure durability for frequent use in communal settings.'
        ],
        'additional_accessories': ['Dimming Controllers', 'Vibration Isolation Mounts', 'Cultural Content Management Software'],
        'panel_recommendation': 'Indoor P3-P4mm with warm color temperature and low-noise operation',
        'estimated_brightness': '400-600 nits for serene viewing in traditional settings',
        'setup_steps': [
            '1. Consult with temple authorities to align with cultural and religious guidelines.',
            '2. Position displays discreetly to maintain the sanctity of the space.',
            '3. Use vibration-isolated mounts to prevent disturbances during rituals.',
            '4. Implement gradual dimming for transitions between ceremony phases.',
            '5. Test audio integration carefully to avoid interference with chants or music.',
            '6. Provide training for temple staff on content management and maintenance.'
        ]
    },
    'retail': {
        'tips': [
            'Eye-catching displays to attract customer attention.',
            'Frequent content updates and dynamic messaging.',
            'Consider compact installation spaces.',
            'Energy efficiency for extended operating hours.'
        ],
        'additional_accessories': ['Dynamic Content Software', 'Compact Mounting Solutions', 'Remote Content Management'],
        'panel_recommendation': 'Indoor P2.5-P4mm for retail storefronts',
        'estimated_brightness': '800-1200 nits for bright retail environments',
        'setup_steps': [
            '1. Install in high-visibility areas like windows or entryways.',
            '2. Ensure panels are eye-catching but not overwhelming in a shopping environment.',
            '3. Integrate with retail management systems for real-time content updates.',
            '4. Use energy-efficient modes during non-business hours.',
            '5. Test display performance with actual product imagery and promotions.',
            '6. Plan for easy access for maintenance without disrupting store operations.'
        ]
    },
    'manufacturing factory': {
        'tips': [
            'Durable panels resistant to dust, vibrations, and harsh environments.',
            'High brightness for visibility in well-lit industrial spaces.',
            'Consider safety signage and process monitoring displays.',
            'Ensure compliance with industrial safety standards.'
        ],
        'additional_accessories': ['Rugged Enclosures', 'Vibration Dampeners', 'Industrial Power Supplies', 'Safety Integration Kits'],
        'panel_recommendation': 'Indoor P3-P5mm with high IP rating for dust and moisture resistance',
        'estimated_brightness': '1000-1500 nits for industrial lighting conditions',
        'setup_steps': [
            '1. Assess factory layout for optimal display placement without obstructing workflows.',
            '2. Choose panels with high IP ratings to withstand dust and occasional moisture.',
            '3. Secure mounts to handle vibrations from machinery.',
            '4. Integrate with factory control systems for real-time data display.',
            '5. Ensure displays comply with workplace safety regulations.',
            '6. Schedule maintenance during off-hours to minimize production downtime.'
        ]
    },
    'manufacturer': {
        'tips': [
            'Durable panels resistant to dust, vibrations, and harsh environments.',
            'High brightness for visibility in well-lit industrial spaces.',
            'Consider safety signage and process monitoring displays.',
            'Ensure compliance with industrial safety standards.'
        ],
        'additional_accessories': ['Rugged Enclosures', 'Vibration Dampeners', 'Industrial Power Supplies', 'Safety Integration Kits'],
        'panel_recommendation': 'Indoor P3-P5mm with high IP rating for dust and moisture resistance',
        'estimated_brightness': '1000-1500 nits for industrial lighting conditions',
        'setup_steps': [
            '1. Assess factory layout for optimal display placement without obstructing workflows.',
            '2. Choose panels with high IP ratings to withstand dust and occasional moisture.',
            '3. Secure mounts to handle vibrations from machinery.',
            '4. Integrate with factory control systems for real-time data display.',
            '5. Ensure displays comply with workplace safety regulations.',
            '6. Schedule maintenance during off-hours to minimize production downtime.'
        ]
    },
    'default': {
        'tips': ['Choose based on viewing distance, brightness requirements, and environment.'],
        'additional_accessories': [],
        'panel_recommendation': 'Consult with our team for personalized recommendations',
        'estimated_brightness': 'Depends on installation location',
        'setup_steps': [
            '1. Assess the specific requirements of your location and intended use.',
            '2. Consult with our technical team for tailored recommendations.',
            '3. Plan the installation with safety and accessibility in mind.',
            '4. Test all components in the actual environment before final setup.',
            '5. Schedule regular maintenance to ensure long-term performance.'
        ]
    }
}

def get_recommendations(spec_type: str) -> str:
    if spec_type.lower() == 'indoor':
        recs = ACCESSORY_RECOMMENDATIONS['indoor']
    elif spec_type.lower() == 'outdoor':
        recs = ACCESSORY_RECOMMENDATIONS['outdoor']
    else:
        return ""

    recommendation_text = "\n\n💡 **Recommended Add-ons:**\n"
    for category, items in recs.items():
        recommendation_text += f"- **{category.replace('_', ' ').title()}:** {', '.join(items)}\n"
    return recommendation_text

def get_product_bundles(spec_type: str) -> str:
    spec_type_lower = spec_type.lower()
    if spec_type_lower not in PRODUCT_BUNDLES:
        return ""
    
    bundles = PRODUCT_BUNDLES[spec_type_lower]
    bundle_text = "\n\n🎯 **Complete Kits Available:**\n"
    
    for bundle_key, bundle_info in bundles.items():
        bundle_text += f"\n**{bundle_info['name']}** ({bundle_key.title()}):\n"
        for item_type, item_name in bundle_info['items'].items():
            bundle_text += f"  • {item_type.replace('_', ' ').title()}: {item_name}\n"
    
    return bundle_text

def get_purpose_recommendations(purpose: str) -> str:
    purpose_lower = purpose.lower()
    for key in PURPOSE_RECOMMENDATIONS:
        if key != 'default' and key in purpose_lower:
            recs = PURPOSE_RECOMMENDATIONS[key]
            text = f"\n\n🎯 **Expert Consultant Guide for {key.title()}:**\n"

            text += f"\n📋 **Recommended Panel Type:**\n{recs.get('panel_recommendation', 'Consult with our team')}\n"
            text += f"\n💡 **Brightness Requirement:**\n{recs.get('estimated_brightness', 'Varies')}\n"

            tips = recs.get('tips', [])
            if tips:
                text += "\n📝 **Key Considerations:**\n"
                for tip in tips:
                    text += f"• {tip}\n"

            additional = recs.get('additional_accessories', [])
            if additional:
                text += "\n🔧 **Recommended Accessories:**\n"
                for acc in additional:
                    text += f"• {acc}\n"

            setup_steps = recs.get('setup_steps', [])
            if setup_steps:
                text += "\n🛠️ **Step-by-Step Setup Guide:**\n"
                for step in setup_steps:
                    text += f"{step}\n"

            return text

    recs = PURPOSE_RECOMMENDATIONS['default']
    text = "\n\n🎯 **Expert Consultant Guide:**\n"
    text += f"\n📋 **Recommended Panel Type:**\n{recs.get('panel_recommendation', 'Consult with our team')}\n"
    tips = recs.get('tips', [])
    if tips:
        text += "\n📝 **Key Considerations:**\n"
        for tip in tips:
            text += f"• {tip}\n"
    setup_steps = recs.get('setup_steps', [])
    if setup_steps:
        text += "\n🛠️ **Step-by-Step Setup Guide:**\n"
        for step in setup_steps:
            text += f"{step}\n"
    return text

# Helper lists for quick lookups
ALL_INDOOR_KEYS = list(INDOOR_SPECS.keys())
ALL_OUTDOOR_KEYS = list(OUTDOOR_SPECS.keys())


# ---------------------------
# Intent detection
# ---------------------------
def detect_intent(message: str) -> str:
    m = message.lower().strip()

    # support
    support_keywords = [
        "help", "issue", "problem", "support", "install", "error", "bug",
        "not working", "repair", "fix", "troubleshoot", "flicker", "flickering",
        "blink", "blinking", "no display", "black screen", "fault", "damaged",
        "spares", "spare parts"
    ]

    # panels (explicit)
    panel_keywords = ["indoor panel", "indoor panels", "outdoor panel", "outdoor panels", "indoor", "outdoor"]

    # comparison
    if "compare" in m:
        return "compare"

    # price
    if "price" in m:
        return "price"

    if any(word in m for word in support_keywords):
        return "support"
    if any(phrase in m for phrase in panel_keywords):
        return "panels"
    # guide queries
    if "guide" in m or "how to" in m or "setup" in m or "install" in m:
        return "guide"
    # knowledge queries
    if any(m.startswith(w) for w in ("what", "how", "who", "when", "where", "tell me", "explain", "define")):
        return "knowledge"
    # controllers
    if "controller" in m or "controllers" in m:
        return "controllers"
    # selecting a panel by exact name
    if any(m == key.lower() for key in ALL_INDOOR_KEYS + ALL_OUTDOOR_KEYS):
        return "select_panel"
    # default
    return "general"


# ---------------------------
# Chatbot - handles a conversation flow per session
# ---------------------------
class EnhancedChatbot:
    def __init__(self, session_id: str):
        self.session_id = session_id
        if session_id not in SESSIONS:
            from django.utils import timezone
            SESSIONS[session_id] = {
                "current_step": "greeting",
                "collected": {},
                "last_intent": None,
                "last_message": None,
                "intent_history": [],
                "session_start_time": timezone.now().isoformat(),
                "message_count": 0,
                "product_views": [],
                "comparison_queries": [],
                "knowledge_queries": []
            }
        self.state = SESSIONS[session_id]

    def get_reply(self, message: str) -> dict:
        msg = message.lower().strip()
        intent = detect_intent(message)
        self.state['last_intent'] = intent
        self.state['last_message'] = message
        self.state['message_count'] = self.state.get('message_count', 0) + 1

        if 'intent_history' not in self.state:
            self.state['intent_history'] = []
        self.state['intent_history'].append(intent)

        if intent == "compare" and message not in self.state.get('comparison_queries', []):
            self.state.setdefault('comparison_queries', []).append(message)
        elif intent == "knowledge" and message not in self.state.get('knowledge_queries', []):
            self.state.setdefault('knowledge_queries', []).append(message)
        elif intent == "panels" and message not in self.state.get('product_views', []):
            self.state.setdefault('product_views', []).append(message)

        # Check for session resumption
        is_resumption = self.state.get('message_count', 0) > 1 and 'saved' not in self.state.get('collected', {})
        if is_resumption:
            welcome_back = "Welcome back! Let's continue from where we left off.\n\n"
        else:
            welcome_back = ""

        log_the_intent_for_analytics = True
        if log_the_intent_for_analytics:
            try:
                session_obj, created = ChatSession.objects.get_or_create(session_id=self.session_id)
                
                selected_panel = self.state.get('collected', {}).get('selected_panel', {}).get('model')
                purpose = self.state.get('collected', {}).get('purpose')
                
                collected_data = self.state.get('collected', {})
                user_interests = {
                    'panel_type': collected_data.get('selected_panel', {}).get('type'),
                    'panel_model': collected_data.get('selected_panel', {}).get('model'),
                    'purpose': collected_data.get('purpose'),
                    'quantity': collected_data.get('quantity'),
                    'include_controller': collected_data.get('include_controller'),
                    'installation_required': collected_data.get('installation'),
                    'screen_width': collected_data.get('width'),
                    'screen_height': collected_data.get('height'),
                    'delivery_location': collected_data.get('delivery'),
                    'company_name': collected_data.get('company_name'),
                    'contact_person': collected_data.get('contact_person'),
                    'mobile': collected_data.get('mobile'),
                    'email': collected_data.get('email'),
                    'intent_history': self.state.get('intent_history', []),
                    'current_step': self.state.get('current_step'),
                    'conversation_depth': len(self.state.get('intent_history', [])),
                    'message_count': self.state.get('message_count', 0),
                    'product_views': self.state.get('product_views', []),
                    'comparison_queries': self.state.get('comparison_queries', []),
                    'knowledge_queries': self.state.get('knowledge_queries', []),
                    'session_start_time': self.state.get('session_start_time')
                }
                
                suggested_products = None
                if intent == "panel_details" or intent == "panel_selection":
                    panel_type = collected_data.get('selected_panel', {}).get('type')
                    if panel_type:
                        bundles = PRODUCT_BUNDLES.get(panel_type, {})
                        recs = ACCESSORY_RECOMMENDATIONS.get(panel_type, {})
                        suggested_products = {
                            'bundles': bundles,
                            'accessories': recs
                        }

                ChatLog.objects.create(
                    session=session_obj,
                    intent=intent,
                    message=message,
                    selected_panel=selected_panel,
                    purpose=purpose,
                    user_interests=user_interests,
                    suggested_products=suggested_products
                )
            except Exception as e:
                print(f"Error logging chat: {e}")

        # Handle specific intents first, regardless of current step
        if intent == "compare":
            response = self._handle_compare(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "panels":
            response = self._handle_panels_request(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "select_panel":
            response = self._show_panel_details(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "guide":
            response = self._handle_guide(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "knowledge":
            response = self._handle_knowledge(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "controllers":
            response = self._wrap("We offer LED controllers such as Nova, Colorlight, and others for managing display signals. Controllers are essential for powering and controlling the panels. Compatibility depends on the panel model; please select a panel to get specific recommendations.", "controllers")
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "price":
            response = self._handle_price(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif intent == "support":
            m = message.lower()
            if "flicker" in m or "flickering" in m:
                response = self._wrap("Flickering can be caused by power supply issues, loose connections, faulty controllers, or incorrect software settings. Please check these first. If the issue persists, contact our technical team at support@xigi.com or call +1-800-123-4567.", "support")
            elif "spares" in m or "spare parts" in m:
                response = self._wrap("For spare parts availability, please contact our support team at support@xigi.com or call +1-800-123-4567.", "support")
            else:
                response = self._wrap("For support issues, please contact our technical team at support@xigi.com or call +1-800-123-4567.", "support")
            response['reply'] = welcome_back + response['reply']
            return response

        # 2. Direct Purpose Input
        if any(word in msg for word in PURPOSE_RECOMMENDATIONS.keys()):
            response = self._handle_application_purpose(msg)
            response['reply'] = welcome_back + response['reply']
            return response

        # routing based on current step for linear conversation flow
        current_step = self.state.get('current_step', 'greeting')

        if current_step == 'greeting':
            response = self._handle_greeting(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'panel_category':
            response = self._handle_panel_category(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'panel_selection':
            response = self._handle_panel_selection(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'application_purpose':
            response = self._handle_application_purpose(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'size_input':
            response = self._handle_size_input(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'quantity_input':
            response = self._handle_quantity_input(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'controller_inclusion':
            response = self._handle_controller_inclusion(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'installation':
            response = self._handle_installation(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'delivery_location':
            response = self._handle_delivery_location(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'client_info':
            response = self._handle_client_info(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'contact_person':
            response = self._handle_contact_person(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'mobile_number':
            response = self._handle_mobile_number(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'email_address':
            response = self._handle_email_address(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'review_confirmation':
            response = self._handle_review_confirmation(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'final_action':
            response = self._handle_final_action(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'modify_options':
            response = self._handle_modify_options(message)
            response['reply'] = welcome_back + response['reply']
            return response
        elif current_step == 'multiple_modifications':
            response = self._handle_multiple_modifications(message)
            response['reply'] = welcome_back + response['reply']
            return response

        # Check for stateful follow-up if in collection mode
        follow_up = self._stateful_follow_up(message)
        if follow_up:
            follow_up['reply'] = welcome_back + follow_up['reply']
            return follow_up

        # fallback general
        response = self._wrap("Good afternoon. How can I assist you today? You can ask for 'indoor panels' or 'outdoor panels'.", "general")
        response['reply'] = welcome_back + response['reply']
        return response

    def _handle_greeting(self, message: str) -> dict:
        self.state['current_step'] = 'application_purpose'
        return self._wrap(STEPS['greeting']['message'], "greeting")

    def _handle_panel_category(self, message: str) -> dict:
        m = message.lower()
        if "indoor" in m:
            self.state['collected']['panel_type'] = 'indoor'
            self.state['current_step'] = 'panel_selection'
            return {
                "session_id": self.session_id,
                "reply": STEPS['panel_category']['message'],
                "intent": "panel_category",
                "type": "buttons",
                "category": "indoor",
                "buttons": ALL_INDOOR_KEYS
            }
        elif "outdoor" in m:
            self.state['collected']['panel_type'] = 'outdoor'
            self.state['current_step'] = 'panel_selection'
            return {
                "session_id": self.session_id,
                "reply": STEPS['panel_category']['message'],
                "intent": "panel_category",
                "type": "buttons",
                "category": "outdoor",
                "buttons": ALL_OUTDOOR_KEYS
            }
        else:
            return self._wrap("Please specify 'indoor' or 'outdoor' for the panels.", "panel_category")

    def _handle_panel_selection(self, message: str) -> dict:
        key = self._normalize_key(message)
        panel_type = self.state['collected'].get('panel_type')
        specs = INDOOR_SPECS if panel_type == 'indoor' else OUTDOOR_SPECS
        if key in specs:
            self.state['collected']['selected_panel'] = {'type': panel_type, 'model': key}

            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Panel updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'size_input'

                panel_details = specs[key]
                formatted_specs = self._format_specs(key, panel_details, "Selected" if panel_type == 'indoor' else "Selected Outdoor")
                product_bundles = get_product_bundles(panel_type)
                product_recs = get_recommendations(panel_type)

                message = f"Great choice! You've selected **{key}**.\n\n{formatted_specs}{product_bundles}{product_recs}\n\n{STEPS['size_input']['message']}"
                return self._wrap(message, "panel_selection")
        else:
            return self._wrap("Please select a valid panel from the list.", "panel_selection")

    def _handle_application_purpose(self, message: str) -> dict:
        if len(message.strip()) > 2:
            purpose = message.strip()
            self.state['collected']['purpose'] = purpose

            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Purpose updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'panel_category'

                purpose_guidance = get_purpose_recommendations(purpose)
                next_step = STEPS['application_purpose']['message']

                # Suggest panel type based on purpose
                suggested_panel_type = None
                for key, recs in PURPOSE_RECOMMENDATIONS.items():
                    if key != 'default' and key in purpose.lower():
                        suggested_panel_type = recs.get('panel_type', 'indoor')
                        break
                if not suggested_panel_type:
                    suggested_panel_type = 'indoor'  # default

                if suggested_panel_type == 'indoor':
                    buttons = ALL_INDOOR_KEYS
                    category = 'indoor'
                else:
                    buttons = ALL_OUTDOOR_KEYS
                    category = 'outdoor'

                consultant_message = f"Perfect! I see you're setting up a {purpose}.\n{purpose_guidance}\n\nBased on your purpose, I recommend **{suggested_panel_type.title()} Panels**. {next_step}"
                return {
                    "session_id": self.session_id,
                    "reply": consultant_message,
                    "intent": "application_purpose",
                    "type": "buttons",
                    "category": category,
                    "buttons": buttons
                }
        else:
            return self._wrap("Please provide a valid application purpose (e.g., 'Event Hall', 'Studio', 'Mall', 'Outdoor Stage', 'Church', 'Retail').", "application_purpose")

    def _handle_size_input(self, message: str) -> dict:
        nums = re.findall(r"(\d+(?:\.\d+)?)", message)
        if len(nums) >= 2:
            self.state['collected']['width'] = float(nums[0])
            self.state['collected']['height'] = float(nums[1])
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Size updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'quantity_input'
                return self._wrap(STEPS['size_input']['message'], "size_input")
        else:
            return self._wrap("Please enter width and height as two numbers, e.g., '10x6'.", "size_input")

    def _handle_quantity_input(self, message: str) -> dict:
        nums = re.findall(r"(\d+)", message)
        if nums:
            self.state['collected']['quantity'] = int(nums[0])
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Quantity updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'controller_inclusion'
                return self._wrap(STEPS['quantity_input']['message'], "quantity_input")
        else:
            return self._wrap("Please enter a number for quantity.", "quantity_input")

    def _handle_controller_inclusion(self, message: str) -> dict:
        m = message.lower()
        if m in ("yes", "y", "include", "sure"):
            self.state['collected']['include_controller'] = True
        elif m in ("no", "n", "skip"):
            self.state['collected']['include_controller'] = False
        else:
            return self._wrap("Please answer 'yes' or 'no'.", "controller_inclusion")

        if self.state.get('modifying'):
            self.state['current_step'] = 'review_confirmation'
            summary = self._build_summary(self.state['collected'])
            return {
                "session_id": self.session_id,
                "reply": f"Controller inclusion updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                "intent": "review_confirmation",
                "type": "summary",
                "summary": self.state['collected']
            }
        else:
            self.state['current_step'] = 'installation'
            return self._wrap(STEPS['controller_inclusion']['message'], "controller_inclusion")

    def _handle_installation(self, message: str) -> dict:
        m = message.lower()
        if m in ("yes", "y"):
            self.state['collected']['installation'] = True
        elif m in ("no", "n"):
            self.state['collected']['installation'] = False
        else:
            return self._wrap("Please answer 'yes' or 'no' for installation.", "installation")

        if self.state.get('modifying'):
            self.state['current_step'] = 'review_confirmation'
            summary = self._build_summary(self.state['collected'])
            return {
                "session_id": self.session_id,
                "reply": f"Installation requirement updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                "intent": "review_confirmation",
                "type": "summary",
                "summary": self.state['collected']
            }
        else:
            self.state['current_step'] = 'delivery_location'
            return self._wrap(STEPS['installation']['message'], "installation")

    def _handle_delivery_location(self, message: str) -> dict:
        if len(message.strip()) > 1:
            self.state['collected']['delivery'] = message.strip()
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Delivery location updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'client_info'
                return self._wrap(STEPS['delivery_location']['message'], "delivery_location")
        else:
            return self._wrap("Please provide a valid delivery location.", "delivery_location")

    def _handle_client_info(self, message: str) -> dict:
        if len(message.strip()) > 1:
            self.state['collected']['company_name'] = message.strip()
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Company name updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'contact_person'
                return self._wrap(STEPS['client_info']['message'], "client_info")
        else:
            return self._wrap("Please provide a valid company name.", "client_info")

    def _handle_contact_person(self, message: str) -> dict:
        if len(message.strip()) > 1:
            self.state['collected']['contact_person'] = message.strip()
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Contact person updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'mobile_number'
                return self._wrap(STEPS['contact_person']['message'], "contact_person")
        else:
            return self._wrap("Please provide a valid contact person name.", "contact_person")

    def _handle_mobile_number(self, message: str) -> dict:
        phone = self._extract_phone(message)
        if phone:
            self.state['collected']['mobile'] = phone
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Mobile number updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'email_address'
                return self._wrap(STEPS['mobile_number']['message'], "mobile_number")
        else:
            return self._wrap("Please provide a valid mobile number.", "mobile_number")

    def _handle_email_address(self, message: str) -> dict:
        email = self._extract_email(message)
        if email:
            self.state['collected']['email'] = email
            if self.state.get('modifying'):
                self.state['current_step'] = 'review_confirmation'
                summary = self._build_summary(self.state['collected'])
                return {
                    "session_id": self.session_id,
                    "reply": f"Email address updated! Here is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
                    "intent": "review_confirmation",
                    "type": "summary",
                    "summary": self.state['collected']
                }
            else:
                self.state['current_step'] = 'review_confirmation'
                return self._wrap(STEPS['email_address']['message'], "email_address")
        else:
            return self._wrap("Please provide a valid email address.", "email_address")

    def _handle_review_confirmation(self, message: str) -> dict:
        m = message.lower()
        if m in ("yes", "y"):
            summary = self._build_summary(self.state['collected'])
            self.state['current_step'] = 'final_action'
            return {
                "session_id": self.session_id,
                "reply": f"Here is the summary of your configuration:\n\n{summary}\n\nWould you like to save this configuration or modify something? (Save/Modify)",
                "intent": "review_confirmation",
                "type": "summary",
                "summary": self.state['collected']
            }
        elif m in ("no", "n"):
            return self._wrap("Okay. What would you like to change? (panel, size, quantity, delivery, contact)", "review_confirmation")
        else:
            return self._wrap("Please answer 'yes' or 'no' to review.", "review_confirmation")

    def _handle_final_action(self, message: str) -> dict:
        m = message.lower()
        if "save" in m:
            self.state['collected']['saved'] = True
            summary = self._build_summary(self.state['collected'])
            try:
                session_obj, created = ChatSession.objects.get_or_create(session_id=self.session_id)
                ChatLog.objects.create(
                    session=session_obj,
                    intent="save_configuration",
                    message="Configuration saved",
                    selected_panel=self.state['collected'].get('selected_panel', {}).get('model'),
                    purpose=self.state['collected'].get('purpose'),
                    user_interests=self.state['collected'],
                    suggested_products=None,
                    configuration_summary=summary
                )
            except Exception as e:
                print(f"Error saving configuration: {e}")
            return self._wrap(STEPS['final_action']['message'], "final_action")
        elif "modify" in m:
            self.state['current_step'] = 'modify_options'
            return self._wrap(STEPS['modify_options']['message'], "modify_options")
        else:
            return self._wrap("Please reply 'save' or 'modify'.", "final_action")

    def _handle_modify_options(self, message: str) -> dict:
        m = message.lower().strip()
        collected = self.state['collected']
        self.state['modifying'] = True  # Set flag to indicate we're in modify mode

        # Check if multiple items are mentioned
        modifications = []
        if 'size' in m:
            modifications.append('size')
        if 'quantity' in m:
            modifications.append('quantity')
        if 'delivery' in m or 'location' in m:
            modifications.append('delivery')
        if 'purpose' in m:
            modifications.append('purpose')
        if 'panel' in m:
            modifications.append('panel')
        if 'controller' in m:
            modifications.append('controller')
        if 'installation' in m:
            modifications.append('installation')
        if 'contact' in m:
            modifications.append('contact')

        if len(modifications) > 1:
            # Multiple modifications requested
            self.state['pending_modifications'] = modifications
            self.state['current_step'] = 'multiple_modifications'
            prompt_parts = []
            for mod in modifications:
                if mod == 'size':
                    prompt_parts.append("size (e.g., '10x6 ft')")
                elif mod == 'quantity':
                    prompt_parts.append("quantity (number)")
                elif mod == 'delivery':
                    prompt_parts.append("delivery location")
                elif mod == 'purpose':
                    prompt_parts.append("purpose")
                elif mod == 'panel':
                    prompt_parts.append("panel type")
                elif mod == 'controller':
                    prompt_parts.append("controller inclusion (yes/no)")
                elif mod == 'installation':
                    prompt_parts.append("installation (yes/no)")
                elif mod == 'contact':
                    prompt_parts.append("contact info")
            prompt = f"Please provide the new values for: {', '.join(prompt_parts)}. Separate each value with a comma."
            return self._wrap(prompt, "multiple_modifications")
        elif len(modifications) == 1:
            # Single modification
            mod = modifications[0]
            if mod == 'size':
                self.state['current_step'] = 'size_input'
                return self._wrap("Please enter your new screen width and height in feet/meters (e.g., '10x6 ft').", "modify_size")
            elif mod == 'quantity':
                self.state['current_step'] = 'quantity_input'
                return self._wrap("How many panels do you need now?", "modify_quantity")
            elif mod == 'delivery':
                self.state['current_step'] = 'delivery_location'
                return self._wrap("Please provide the new delivery location.", "modify_delivery")
            elif mod == 'purpose':
                self.state['current_step'] = 'application_purpose'
                return self._wrap("Where will you use the LED panel? (e.g., Mall, Event Hall, Studio, Outdoor Stage, Church)", "modify_purpose")
            elif mod == 'panel':
                self.state['current_step'] = 'panel_category'
                return self._wrap("Would you like to change to indoor or outdoor panels?", "modify_panel")
            elif mod == 'controller':
                self.state['current_step'] = 'controller_inclusion'
                return self._wrap("Would you like to include controller, cabinets, and mounting structure? (Yes/No)", "modify_controller")
            elif mod == 'installation':
                self.state['current_step'] = 'installation'
                return self._wrap("Do you need on-site installation support? (Yes/No)", "modify_installation")
            elif mod == 'contact':
                self.state['current_step'] = 'client_info'
                return self._wrap("Please provide your company name.", "modify_contact")
        else:
            return self._wrap("Please specify what to modify: size, quantity, delivery, purpose, panel, controller, installation, or contact.", "modify_options")

    def _handle_multiple_modifications(self, message: str) -> dict:
        if 'pending_modifications' not in self.state:
            return self._wrap("No pending modifications found. Please try again.", "modify_options")

        modifications = self.state['pending_modifications']
        values = [v.strip() for v in message.split(',')]

        if len(values) != len(modifications):
            return self._wrap(f"Please provide exactly {len(modifications)} values separated by commas.", "multiple_modifications")

        updated_fields = []
        for i, mod in enumerate(modifications):
            value = values[i]
            if mod == 'size':
                nums = re.findall(r"(\d+(?:\.\d+)?)", value)
                if len(nums) >= 2:
                    self.state['collected']['width'] = float(nums[0])
                    self.state['collected']['height'] = float(nums[1])
                    updated_fields.append("size")
                else:
                    return self._wrap("Invalid size format. Please use format like '10x6 ft'.", "multiple_modifications")
            elif mod == 'quantity':
                nums = re.findall(r"(\d+)", value)
                if nums:
                    self.state['collected']['quantity'] = int(nums[0])
                    updated_fields.append("quantity")
                else:
                    return self._wrap("Invalid quantity. Please provide a number.", "multiple_modifications")
            elif mod == 'delivery':
                if len(value.strip()) > 1:
                    self.state['collected']['delivery'] = value.strip()
                    updated_fields.append("delivery location")
                else:
                    return self._wrap("Invalid delivery location.", "multiple_modifications")
            elif mod == 'purpose':
                if len(value.strip()) > 2:
                    self.state['collected']['purpose'] = value.strip()
                    updated_fields.append("purpose")
                else:
                    return self._wrap("Invalid purpose.", "multiple_modifications")
            elif mod == 'panel':
                # For panel, we'll assume they provide the panel type (indoor/outdoor) and handle it later
                if 'indoor' in value.lower():
                    self.state['collected']['panel_type'] = 'indoor'
                    updated_fields.append("panel type to indoor")
                elif 'outdoor' in value.lower():
                    self.state['collected']['panel_type'] = 'outdoor'
                    updated_fields.append("panel type to outdoor")
                else:
                    return self._wrap("Please specify 'indoor' or 'outdoor' for panel type.", "multiple_modifications")
            elif mod == 'controller':
                if value.lower() in ('yes', 'y', 'include', 'sure'):
                    self.state['collected']['include_controller'] = True
                    updated_fields.append("controller inclusion")
                elif value.lower() in ('no', 'n', 'skip'):
                    self.state['collected']['include_controller'] = False
                    updated_fields.append("controller inclusion")
                else:
                    return self._wrap("Please specify 'yes' or 'no' for controller.", "multiple_modifications")
            elif mod == 'installation':
                if value.lower() in ('yes', 'y'):
                    self.state['collected']['installation'] = True
                    updated_fields.append("installation")
                elif value.lower() in ('no', 'n'):
                    self.state['collected']['installation'] = False
                    updated_fields.append("installation")
                else:
                    return self._wrap("Please specify 'yes' or 'no' for installation.", "multiple_modifications")
            elif mod == 'contact':
                # For contact, we'll update company name as representative
                if len(value.strip()) > 1:
                    self.state['collected']['company_name'] = value.strip()
                    updated_fields.append("contact info")
                else:
                    return self._wrap("Invalid contact info.", "multiple_modifications")

        # Clear pending modifications
        del self.state['pending_modifications']
        self.state['current_step'] = 'review_confirmation'

        summary = self._build_summary(self.state['collected'])
        return {
            "session_id": self.session_id,
            "reply": f"Updated: {', '.join(updated_fields)}!\n\nHere is the updated summary:\n\n{summary}\n\nWould you like to save this configuration or modify something else? (Save/Modify)",
            "intent": "review_confirmation",
            "type": "summary",
            "summary": self.state['collected']
        }

    # Panels intent - return list of panel names as buttons
    def _handle_panels_request(self, message: str) -> dict:
        m = message.lower()
        if "indoor" in m:
            # return only names and type indicator
            return {
                "session_id": self.session_id,
                "reply": "Here are our indoor panels. Click one to see full specifications.",
                "intent": "panels",
                "type": "buttons",
                "category": "indoor",
                "buttons": ALL_INDOOR_KEYS
            }
        if "outdoor" in m:
            return {
                "session_id": self.session_id,
                "reply": "Here are our outdoor panels. Click one to see full specifications.",
                "intent": "panels",
                "type": "buttons",
                "category": "outdoor",
                "buttons": ALL_OUTDOOR_KEYS
            }
        # if ambiguous
        return self._wrap("Do you want indoor or outdoor panels? Please say 'indoor panels' or 'outdoor panels'.", "panels")

    # When user clicks a panel button (frontend should send the panel name as message)
    def _show_panel_details(self, message: str) -> dict:
        key = self._normalize_key(message)
        if key in INDOOR_SPECS:
            if key not in self.state.get('product_views', []):
                self.state.setdefault('product_views', []).append(key)

            formatted = self._format_specs(key, INDOOR_SPECS[key], "Indoor")
            recommendations = get_recommendations('indoor')
            product_bundles = get_product_bundles('indoor')
            self.state['collected']['selected_panel'] = {'type': 'indoor', 'model': key}

            if 'purpose' in self.state['collected']:
                self.state['current_step'] = 'size_input'
                follow = f"\n\n{STEPS['size_input']['message']}"
            else:
                follow = "\n\nNext, tell me: **Where will you use this panel?** (e.g., Mall, Event Hall, Studio, Outdoor Stage, Church, Retail)"
            return {
                "session_id": self.session_id,
                "reply": f"**Perfect Choice: {key}**\n\n{formatted}{product_bundles}{recommendations}{follow}",
                "intent": "panel_details",
                "panel": key
            }
        if key in OUTDOOR_SPECS:
            if key not in self.state.get('product_views', []):
                self.state.setdefault('product_views', []).append(key)

            formatted = self._format_specs(key, OUTDOOR_SPECS[key], "Outdoor")
            recommendations = get_recommendations('outdoor')
            product_bundles = get_product_bundles('outdoor')
            self.state['collected']['selected_panel'] = {'type': 'outdoor', 'model': key}

            if 'purpose' in self.state['collected']:
                self.state['current_step'] = 'size_input'
                follow = f"\n\n{STEPS['size_input']['message']}"
            else:
                follow = "\n\nNext, tell me: **Where will you use this panel?** (e.g., Mall, Event Hall, Studio, Outdoor Stage, Church, Retail)"
            return {
                "session_id": self.session_id,
                "reply": f"**Perfect Choice: {key}**\n\n{formatted}{product_bundles}{recommendations}{follow}",
                "intent": "panel_details",
                "panel": key
            }
        return self._wrap("I couldn't find that panel. Please click a button from the list or type the exact model name.", "error")

    # Compare two models - parse message for two panel names
    def _handle_compare(self, message: str) -> dict:
        # naive parse: extract tokens like P3mm, P4mm, P3.91mm etc.
        tokens = re.findall(r"p\d+(?:\.\d+)?mm", message.lower())
        unique = []
        for t in tokens:
            if t not in unique:
                unique.append(t)
        if len(unique) < 2:
            return self._wrap("Please specify two panel models to compare, e.g. 'Compare P3mm and P4mm'.", "compare")
        a, b = unique[0].upper(), unique[1].upper()
        # normalize keys possible variants (P3mm vs P3.0mm)
        a_key = self._match_panel_key(a)
        b_key = self._match_panel_key(b)
        if not a_key or not b_key:
            return self._wrap(f"Couldn't find one or both panels ({a},{b}). Please use exact model names from lists.", "compare")
        # build comparison
        details_a = INDOOR_SPECS.get(a_key) or OUTDOOR_SPECS.get(a_key)
        details_b = INDOOR_SPECS.get(b_key) or OUTDOOR_SPECS.get(b_key)
        comp = self._format_comparison(a_key, details_a, b_key, details_b)
        return {
            "session_id": self.session_id,
            "reply": comp,
            "intent": "compare"
        }

    # Handle simple knowledge queries or manufacturer question
    def _handle_knowledge(self, message: str) -> dict:
        m = message.lower()
        if "pixel pitch" in m:
            return self._wrap("Pixel pitch is the distance between two adjacent pixels. Smaller pitch yields higher clarity and is used for closer viewing distances.", "knowledge")
        if "manufacturer" in m or "who makes" in m or "who is the manufacturer" in m:
            return self._wrap("Our panels are supplied under XIGI Tech / authorized manufacturing partners. For exact origin per model please request details for that model.", "knowledge")
        if "how often" in m and "clean" in m:
            return self._wrap("Clean LED panels every 2–4 weeks with a soft, dry microfiber cloth. Avoid water or harsh chemicals.", "knowledge")
        if "controller" in m or "controllers" in m:
            return self._wrap("We offer LED controllers such as Nova, Colorlight, and others for managing display signals. Controllers are essential for powering and controlling the panels. Compatibility depends on the panel model; please select a panel to get specific recommendations.", "knowledge")
        if "software" in m:
            return self._wrap("We use software compatible with our LED controllers, such as NovaStar's LED Studio or Colorlight's software, for programming and controlling LED displays.", "knowledge")
        # fallback
        return self._wrap("Could you clarify your question? Ask about pixel pitch, manufacturer, cleaning, controllers, software, or a specific panel model.", "knowledge")

    # Handle price queries
    def _handle_price(self, message: str) -> dict:
        m = message.lower()
        # Extract panel names using regex
        tokens = re.findall(r"p\d+(?:\.\d+)?mm", m)
        if tokens:
            panel_key = self._match_panel_key(tokens[0].upper())
            if panel_key:
                specs = INDOOR_SPECS.get(panel_key) or OUTDOOR_SPECS.get(panel_key)
                if specs:
                    price_sq = specs.get('price_per_sq_meter', 'Not available')
                    price_cab = specs.get('price_per_cabinet', 'Not available')
                    return self._wrap(f"Price for {panel_key}:\n- Per Sq. Meter: {price_sq}\n- Per Cabinet: {price_cab}", "price")
                else:
                    return self._wrap(f"Price information for {panel_key} is not available.", "price")
            else:
                return self._wrap("Please specify a valid panel model, e.g., 'price of P3mm'.", "price")
        else:
            # General price query
            return self._wrap("Prices vary by model. Please specify a panel, e.g., 'price of P3mm' or 'price of indoor panels'. For a full list, ask for 'indoor panels' or 'outdoor panels'.", "price")

    # Handle guide queries
    def _handle_guide(self, message: str) -> dict:
        purpose = self.state.get('collected', {}).get('purpose')
        if not purpose:
            return self._wrap("To provide a detailed setup guide, please tell me the purpose of your LED display (e.g., Event Hall, Church, Temple, Mall, Outdoor Stage, Studio, Retail).", "guide")
        guide_text = get_purpose_recommendations(purpose)
        return self._wrap(f"Here's the detailed guide for {purpose}:{guide_text}", "guide")

    # Stateful follow-up: collects purpose, size, quantity, controller inclusion, delivery, client info, then review
    def _stateful_follow_up(self, message: str):
        c = self.state['collected']
        m = message.strip()

        # If user selected a panel earlier and we haven't asked for purpose or stored it yet
        if 'selected_panel' in c and 'purpose' not in c:
            # If user provided a purpose (detect common words)
            if len(m) > 2 and not m.isdigit():
                c['purpose'] = m
                return self._wrap("Noted. Please provide screen width and height in feet (e.g., '10 ft x 6 ft' or '10x6').", "collect_purpose")
            else:
                return self._wrap("Where will you use this panel? (Mall, Event Hall, Studio, Outdoor Stage, Church)", "collect_purpose")

        # Size parsing
        if 'selected_panel' in c and 'purpose' in c and ('width' not in c or 'height' not in c):
            # parse "10 x 6", "10x6", "10 ft x 6 ft", or two numbers
            nums = re.findall(r"(\d+(?:\.\d+)?)", m)
            if len(nums) >= 2:
                width = float(nums[0])
                height = float(nums[1])
                c['width'] = width
                c['height'] = height
                return self._wrap(f"Got size: {width} x {height} (ft). How many identical displays (quantity) do you need?", "collect_size")
            else:
                return self._wrap("Please enter width and height (two numbers). Example: '10x6' or '10 ft x 6 ft'.", "collect_size")

        # Quantity
        if 'width' in c and 'height' in c and 'quantity' not in c:
            nums = re.findall(r"(\d+)", m)
            if nums:
                c['quantity'] = int(nums[0])
                return self._wrap("Do you want us to include a controller, cabinets and mounting structure? (yes/no)", "collect_quantity")
            else:
                return self._wrap("Please enter a number for quantity (e.g., '2').", "collect_quantity")

        # Controller inclusion
        if 'quantity' in c and 'include_controller' not in c:
            if m.lower() in ("yes", "y", "include", "sure"):
                c['include_controller'] = True
                return self._wrap("Do you require on-site installation? (yes/no)", "collect_controller")
            if m.lower() in ("no", "n", "skip"):
                c['include_controller'] = False
                return self._wrap("Do you require on-site installation? (yes/no)", "collect_controller")
            return self._wrap("Please answer 'yes' or 'no' for controller inclusion.", "collect_controller")

        # Installation
        if 'include_controller' in c and 'installation' not in c:
            if m.lower() in ("yes", "y"):
                c['installation'] = True
                return self._wrap("Please provide delivery city or location.", "collect_installation")
            if m.lower() in ("no", "n"):
                c['installation'] = False
                return self._wrap("Please provide delivery city or location.", "collect_installation")
            return self._wrap("Please answer 'yes' or 'no' regarding installation requirement.", "collect_installation")

        # Delivery
        if 'installation' in c and 'delivery' not in c:
            if len(m) > 1:
                c['delivery'] = m
                return self._wrap("Please provide client company name.", "collect_delivery")
            return self._wrap("Please provide a delivery location (city/address).", "collect_delivery")

        # Client info: company, contact name, phone, email
        if 'delivery' in c and 'company_name' not in c:
            c['company_name'] = m
            return self._wrap("Client contact person name?", "collect_company")
        if 'company_name' in c and 'contact_person' not in c:
            c['contact_person'] = m
            return self._wrap("Mobile number of contact person?", "collect_contact")
        if 'contact_person' in c and 'mobile' not in c:
            phone = self._extract_phone(m)
            if phone:
                c['mobile'] = phone
                return self._wrap("Email of contact person?", "collect_mobile")
            else:
                return self._wrap("Please provide a valid mobile number (digits only).", "collect_mobile")
        if 'mobile' in c and 'email' not in c:
            email = self._extract_email(m)
            if email:
                c['email'] = email
                return self._wrap("All done. Would you like to review the gathered configuration? (yes/no)", "collect_email")
            else:
                return self._wrap("Please provide a valid email address.", "collect_email")

        # Final review and summary
        if 'email' in c and 'reviewed' not in c:
            if m.lower() in ("yes", "y"):
                c['reviewed'] = True
                summary = self._build_summary(c)
                return {
                    "session_id": self.session_id,
                    "reply": "Here is the summary of your configuration:\n\n" + summary + "\n\nWould you like to (1) save this configuration or (2) modify anything? Reply 'save' or 'modify'.",
                    "intent": "review",
                    "type": "summary",
                    "summary": c
                }
            if m.lower() in ("no", "n"):
                return self._wrap("Okay. What would you like to change? (e.g., 'change quantity' or 'change panel')", "review")
            return self._wrap("Please answer 'yes' to review or 'no' to modify.", "review")

        if 'reviewed' in c:
            if "save" in m.lower():
                c['saved'] = True
                return self._wrap("Configuration saved. Our sales team can contact you for pricing and next steps.", "saved")
            if "modify" in m.lower():
                c.pop('reviewed', None)
                self.state['current_step'] = 'modify_options'
                return self._wrap(STEPS['modify_options']['message'], "modify_options")
            return self._wrap("Please reply 'save' to save configuration or 'modify' to change details.", "review_action")

        return None

    # ---------------------------
    # Utility helpers
    # ---------------------------
    def _wrap(self, text: str, intent: str) -> dict:
        return {"session_id": self.session_id, "reply": text, "intent": intent}

    def _normalize_key(self, msg: str) -> str:
        # Accept variants: "p3mm", "P3mm", "p3.91mm", "p391", etc.
        s = msg.strip()
        # If exact match in keys
        if s in INDOOR_SPECS or s in OUTDOOR_SPECS:
            return s
        up = s.upper()
        # try uppercase keys
        for k in list(INDOOR_SPECS.keys()) + list(OUTDOOR_SPECS.keys()):
            if k.upper() == up:
                return k
        # try adding 'mm' if missing
        if not up.endswith("MM"):
            up2 = up + "MM"
            for k in list(INDOOR_SPECS.keys()) + list(OUTDOOR_SPECS.keys()):
                if k.upper() == up2:
                    return k
        return s

    def _match_panel_key(self, pattern: str):
        # pattern like 'P3MM' or 'P3.91MM'
        for k in list(INDOOR_SPECS.keys()) + list(OUTDOOR_SPECS.keys()):
            if k.upper().replace('.', '') == pattern.replace('.', ''):
                return k
        # direct match
        for k in list(INDOOR_SPECS.keys()) + list(OUTDOOR_SPECS.keys()):
            if k.upper() == pattern:
                return k
        return None

    def _format_specs(self, pitch: str, details: dict, category: str) -> str:
        out = f"{category} Panel - {pitch}\n"
        out += f"Pixel Pitch: {details.get('pixel_pitch', pitch)}\n"
        out += f"Module Resolution: {', '.join(details.get('module_resolutions', []))}\n"
        out += f"LED Type: {', '.join(details.get('led_types', []))}\n"
        out += f"Brightness: {', '.join(details.get('brightness_options', []))}\n"
        out += f"Module Size: {', '.join(details.get('module_sizes', []))}\n"
        if details.get('scan_times'):
            out += f"Scan Time: {', '.join(details.get('scan_times'))}\n"
        if details.get('driving_modes'):
            out += f"Driving Mode: {', '.join(details.get('driving_modes'))}\n"
        out += f"IP Rating: {details.get('ip_rating')}\n"
        if details.get('price_per_sq_meter'):
            out += f"Price per Sq.Meter: {details.get('price_per_sq_meter')}\n"
        if details.get('price_per_cabinet'):
            out += f"Price per Cabinet: {details.get('price_per_cabinet')}\n"
        return out

    def _format_comparison(self, a_key, a_details, b_key, b_details):
        def one_line(d, field, default='-'):
            val = d.get(field)
            if isinstance(val, list):
                return ', '.join(val)
            return val or default
        rows = [
            ("Model", a_key, b_key),
            ("Pixel Pitch", one_line(a_details, 'pixel_pitch'), one_line(b_details, 'pixel_pitch')),
            ("Module Resolution", one_line(a_details, 'module_resolutions'), one_line(b_details, 'module_resolutions')),
            ("Brightness", one_line(a_details, 'brightness_options'), one_line(b_details, 'brightness_options')),
            ("Module Size", one_line(a_details, 'module_sizes'), one_line(b_details, 'module_sizes')),
            ("IP Rating", one_line(a_details, 'ip_rating'), one_line(b_details, 'ip_rating')),
            ("Price / Sq.m", one_line(a_details, 'price_per_sq_meter', '-'), one_line(b_details, 'price_per_sq_meter', '-'))
        ]
        text = "Comparison:\n"
        for r in rows:
            text += f"{r[0]}: {r[1]}  |  {r[2]}\n"
        return text

    def _extract_email(self, text: str):
        m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        return m.group(0) if m else None

    def _extract_phone(self, text: str):
        m = re.search(r'(\+?\d{7,15})', text)
        return m.group(1) if m else None

    def _build_summary(self, c: dict) -> str:
        parts = []
        sel = c.get('selected_panel', {})
        if sel:
            parts.append(f"Type: {sel.get('type')}, Model: {sel.get('model')}")
        if 'purpose' in c:
            parts.append(f"Purpose: {c['purpose']}")
        if 'width' in c and 'height' in c:
            parts.append(f"Size: {c['width']} x {c['height']} (ft)")
        if 'quantity' in c:
            parts.append(f"Quantity: {c['quantity']}")
        parts.append(f"Include controller: {c.get('include_controller', False)}")
        parts.append(f"Installation required: {c.get('installation', False)}")
        if 'delivery' in c:
            parts.append(f"Delivery: {c['delivery']}")
        if 'company_name' in c:
            parts.append(f"Company: {c['company_name']} (Contact: {c.get('contact_person','')}, {c.get('mobile','')}, {c.get('email','')})")
        return "\n".join(parts)


# ---------------------------
# Analytics API View
# ---------------------------
@method_decorator(csrf_exempt, name='dispatch')
class AnalyticsAPIView(APIView):
    def get(self, request):
        # Top searched panels
        top_panels = ChatLog.objects.values('selected_panel').annotate(count=Count('selected_panel')).order_by('-count')[:10]
        top_panels_data = [{'panel': item['selected_panel'] or 'Unknown', 'count': item['count']} for item in top_panels]

        # Most common purposes
        common_purposes = ChatLog.objects.values('purpose').annotate(count=Count('purpose')).order_by('-count')[:10]
        purposes_data = [{'purpose': item['purpose'] or 'Unknown', 'count': item['count']} for item in common_purposes]

        # Daily user count (unique sessions per day)
        daily_users = ChatSession.objects.annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('session_id', distinct=True)).order_by('date')
        daily_users_data = [{'date': item['date'].isoformat(), 'count': item['count']} for item in daily_users]

        return Response({
            'top_panels': top_panels_data,
            'common_purposes': purposes_data,
            'daily_users': daily_users_data
        }, status=status.HTTP_200_OK)

# ---------------------------
# Chat Sessions and Messages API View with Filters
# ---------------------------
@method_decorator(csrf_exempt, name='dispatch')
class ChatDataAPIView(APIView):
    def get(self, request):
        filter_type = request.query_params.get('filter', 'today')  # today, week, month, year

        now = timezone.now()

        if filter_type == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_type == 'week':
            start_date = now - timedelta(days=7)
        elif filter_type == 'month':
            # Start of current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif filter_type == 'year':
            # Start of current year
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return Response({'error': 'Invalid filter type. Use: today, week, month, year'}, status=status.HTTP_400_BAD_REQUEST)

        # Filter chat sessions
        sessions = ChatSession.objects.filter(created_at__gte=start_date).order_by('-created_at')
        sessions_data = []
        for session in sessions:
            # Get messages for this session
            messages = ChatMessage.objects.filter(session=session, created_at__gte=start_date).order_by('created_at')
            messages_data = [
                {
                    'id': msg.id,
                    'message': msg.message,
                    'response': msg.response,
                    'intent': msg.intent,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages
            ]

            sessions_data.append({
                'session_id': session.session_id,
                'created_at': session.created_at.isoformat(),
                'messages_count': messages.count(),
                'messages': messages_data
            })

        return Response({
            'filter': filter_type,
            'total_sessions': len(sessions_data),
            'sessions': sessions_data
        }, status=status.HTTP_200_OK)

# ---------------------------
# API View
# ---------------------------
@method_decorator(csrf_exempt, name='dispatch')
class AlexaChatAPIView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id") or str(uuid.uuid4())
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({
                "session_id": session_id,
                "reply": "👋 Hi there! I'm XIGI Assistant — your smart LED display guide. 💡\nWould you like to start with Indoor or Outdoor panels?",
                "intent": "greeting"
            })

        # ensure session exists
        if session_id not in SESSIONS:
            SESSIONS[session_id] = {"collected": {}, "last_intent": None, "last_message": None}

        # Get or create ChatSession
        session_obj, created = ChatSession.objects.get_or_create(session_id=session_id)

        bot = EnhancedChatbot(session_id=session_id)
        response = bot.get_reply(message)

        # Save user message
        ChatMessage.objects.create(
            session=session_obj,
            sender='user',
            message=message,
            intent=response.get('intent'),
        )

        # Save bot response
        ChatMessage.objects.create(
            session=session_obj,
            sender='bot',
            message=response.get('reply', ''),
            response=response.get('reply', ''),
            intent=response.get('intent'),
        )

        return Response(response, status=status.HTTP_200_OK)
