import uuid
import re
import os
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from django.conf import settings

# ---------------------------
# In-memory session store (prototype)
# ---------------------------
SESSIONS = {}


class EnhancedChatbot:
    """
    AI LED Assistant - Full Version
    --------------------------------
    • Sales & Product Adviser (controllers, panels, modules, etc.)
    • Pricing & Warranty Guidance  
    • Troubleshooting and Installation Assistance
    • Order & Replacement Support
    • AI Knowledgebase integration for dynamic responses
    • Session-aware with lightweight tracking
    """

    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        # Load session data from global store, or initialize if new
        if self.session_id not in SESSIONS:
            SESSIONS[self.session_id] = {
                'asked_include_accessories': False,
                'include_accessories': None,
                'standee_type': None
            }
        self.session_data = SESSIONS[self.session_id]

        # Initialize AI knowledgebase
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.vector_db = Chroma(
            persist_directory="kb_vectors",
            embedding_function=self.embeddings
        )
        self.llm = OpenAI(temperature=0.0, openai_api_key=settings.OPENAI_API_KEY)

    # --------------------------------------------------------
    # MAIN MESSAGE PROCESSOR
    # --------------------------------------------------------
    def get_reply(self, message: str) -> dict:
        msg = message.lower().strip()

        # Handle initial greeting (empty message)
        if not msg:
            reply = "Hey 👋 I'm XIGI AI Assistant! Ready to explore LED panels?"
            buttons = ["Indoor Panels", "Outdoor Panels", "Rental Panels", "Standee Panels"]
            return self._build_buttons_response(reply, buttons)

        # Handle response to accessories question
        if self.session_data.get('asked_include_accessories'):
            if 'yes' in msg:
                self.session_data['include_accessories'] = True
                self.session_data['asked_include_accessories'] = False
                reply = "Great! We'll include controllers, cabinets, and mounting structure in your quote. What else can I help you with?"
                return self._build_response(reply)
            elif 'no' in msg:
                self.session_data['include_accessories'] = False
                self.session_data['asked_include_accessories'] = False
                reply = "Understood. We'll focus on the panels for now. What else can I help you with?"
                return self._build_response(reply)
            else:
                self.session_data['asked_include_accessories'] = False
                reply = "Understood, let's continue. What else can I help you with?"
                return self._build_response(reply)

        # Standee Panels
        if "standee" in msg or "standee panels" in msg:
            reply = "Standee panels are portable LED displays for events and promotions. We offer A-Type (Android-based) and I-Type (Interactive) models. Which type interests you?"
            buttons = ["A-Type", "I-Type"]
            return self._build_buttons_response(reply, buttons)

        # Handle A-Type selection
        if msg == "a-type":
            self.session_data['standee_type'] = 'a-type'
            reply = "A-Type standee panels are Android-powered for content playback. Choose your preferred size:"
            buttons = ["32inch", "43inch", "55inch", "Custom Size"]
            return self._build_buttons_response(reply, buttons)

        # Handle I-Type selection
        if msg == "i-type":
            self.session_data['standee_type'] = 'i-type'
            reply = "I-Type standee panels are interactive touchscreens. Choose your preferred size:"
            buttons = ["6Hx1W", "6Hx3W", "Custom Size"]
            return self._build_buttons_response(reply, buttons)

        # Handle size selections for A-Type
        if self.session_data.get('standee_type') == 'a-type' and msg in ["32inch", "43inch", "55inch", "custom size"]:
            size = msg
            reply = f"Great! You've selected A-Type {size}. This model features high brightness and Android OS for easy content management. Would you like pricing details or to proceed with a quote?"
            return self._build_response(reply)

        # Handle size selections for I-Type
        if self.session_data.get('standee_type') == 'i-type' and msg in ["6hx1w", "6hx3w", "custom size"]:
            size = msg
            reply = f"Excellent! You've selected I-Type {size}. This interactive model supports touch gestures and multi-user interaction. Would you like pricing details or to proceed with a quote?"
            return self._build_response(reply)

        # 1. Greetings
        if self._is_greeting(msg):
            reply = (
                "Hello! I’m XIGI AI Assistant, your LED Sales and Support Assistant.\n"
                "How can I help you today?"
            )
            return self._build_response(reply)

        # 2. Support Queries
        if any(word in msg for word in ["help", "support", "issue", "problem", "contact", "complaint", "agent", "error", "fix", "installation", "setup"]):
            reply = self._handle_support_query(msg)
            return self._build_response(reply)

        # 3. Controllers
        if "controller" in msg:
            reply = (
                "Controllers manage LED display visuals and data signals.\n"
                "Common models include Novastar VX600, Colorlight X8, and Linsn TS802D.\n"
                "Would you like setup guidance or compatible options?"
            )
            return self._build_response(reply)

        # 4. Pixel Pitch
        if "pixel pitch" in msg:
            reply = (
                "Pixel Pitch is the distance between two LED pixels.\n"
                "Smaller pitch offers sharper indoor visuals, while larger pitch suits outdoor displays.\n"
                "Examples: P2.5 (fine detail), P3.91 (balanced clarity), P6 (outdoor viewing)."
            )
            return self._build_response(reply)

        # 5. Power Supply
        if re.search(r"\b(power supply|adapter|driver)\b", msg):
            reply = (
                "Power supplies convert AC to DC for LED panels.\n"
                "Recommended types include 200W, 350W, and 500W (Meanwell or G-Energy).\n"
                "Would you like details for indoor or outdoor configurations?"
            )
            return self._build_response(reply)

        # 7. LED Panels
        if "led display" in msg or "panel" in msg:
            reply = (
                "LED panels form the display surface of a video wall.\n"
                "Choose based on pixel pitch, brightness, and location (indoor/outdoor).\n"
                "Available types: P1.25, P1.56, P2.5, P3.91, P4.81, P6, P8, P10.\n"
                "Would you like to view comparison details or mounting options?"
            )
            return self._build_response(reply)

        # 8. Receiving / Sending Cards
        if any(word in msg for word in ["receiving card", "sending card", "mrv", "rv", "a8", "a10"]):
            reply = (
                "Receiving and sending cards transmit image data between controllers and panels.\n"
                "Common models: Novastar MRV336, Colorlight A8, Linsn RV908.\n"
                "Would you like help identifying compatible cards for your system?"
            )
            return self._build_response(reply)

        # 8. LED Modules
        if "module" in msg:
            reply = (
                "LED modules are the core building blocks of panels.\n"
                "Indoor: P2.5, P3.91, P4.81 | Outdoor: P6, P8, P10.\n"
                "Would you like details on indoor or outdoor module types?"
            )
            return self._build_response(reply)

        # 9. Cables and Connectors
        if any(word in msg for word in ["cable", "connector", "rj45", "hdmi", "data cable", "power cable"]):
            reply = (
                "LED systems use power and data cables for connectivity.\n"
                "Common types: CAT6, flat ribbon, 5V data cable, HDMI, DP.\n"
                "Would you like wiring layout or connection diagrams?"
            )
            return self._build_response(reply)

        # 10. Cabinets / Frames
        if "cabinet" in msg or "frame" in msg:
            reply = (
                "Cabinets hold LED panels securely in place.\n"
                "Indoor: Die-cast aluminum | Outdoor: Waterproof iron.\n"
                "Would you like to explore standard cabinet sizes or materials?"
            )
            return self._build_response(reply)

        # 11. Video Processors
        if "processor" in msg or "video processor" in msg:
            reply = (
                "Video processors handle input scaling and color correction.\n"
                "Models include Novastar VX1000, Colorlight Z6, Linsn VP620.\n"
                "Would you like to know supported input formats?"
            )
            return self._build_response(reply)

        # 12. Accessories
        if any(word in msg for word in ["accessory", "mount", "bracket", "hanger", "cooling", "fan"]):
            if not self.session_data.get('asked_include_accessories'):
                self.session_data['asked_include_accessories'] = True
                reply = "Would you like to include controller, cabinets, and mounting structure?"
                return self._build_response(reply)
            else:
                reply = (
                    "We also provide accessories such as mounting kits, hanging bars, and cooling fans.\n"
                    "Would you like installation recommendations or model options?"
                )
                return self._build_response(reply)

        # 13. Software / Calibration Tools
        if any(word in msg for word in ["software", "novalct", "ledvision", "ledset", "configuration"]):
            reply = (
                "Software tools are used for LED calibration and configuration.\n"
                "Examples: NovaLCT, Colorlight LEDVision, Linsn LEDSet.\n"
                "Would you like installation or setup instructions?"
            )
            return self._build_response(reply)

        # 14. Spare Parts / Maintenance
        if any(word in msg for word in ["spare", "ic", "hub", "chip", "replacement", "maintenance"]):
            reply = (
                "We offer spare parts such as IC chips, hub boards, and power cables.\n"
                "Would you like help identifying replacements for your panel model?"
            )
            return self._build_response(reply)

        # 15. Warranty
        if "warranty" in msg:
            reply = (
                "All LED products include a 2-year warranty.\n"
                "Controllers and power supplies have a 1-year coverage.\n"
                "Would you like to extend or check warranty eligibility?"
            )
            return self._build_response(reply)

        # 16. Pricing Queries
        if "price" in msg or "cost" in msg or "rate" in msg:
            reply = self._handle_price_query(msg)
            return self._build_response(reply)

        # 17. Order Status or Replacement
        if any(word in msg for word in ["order", "dispatch", "delivery", "replacement", "refund", "track"]):
            reply = self._handle_order_query(msg)
            return self._build_response(reply)

        # 18. Knowledgebase (Fallback)
        reply = self._ai_knowledge_response(msg)
        return self._build_response(reply)

    # --------------------------------------------------------
    # SUPPORT HANDLER
    # --------------------------------------------------------
    def _handle_support_query(self, msg: str) -> str:
        if "problem" in msg or "issue" in msg or "error" in msg:
            return (
                "Please describe your issue. Common fixes include:\n"
                "- No display: Check power and data input.\n"
                "- Flicker: Adjust refresh rate or reconnect signal.\n"
                "- Color shift: Run calibration software.\n"
                "Would you like a troubleshooting guide?"
            )
        if "installation" in msg or "setup" in msg:
            return (
                "Installation involves panel alignment, data cabling, and controller mapping.\n"
                "Would you like a step-by-step installation guide or technician contact?"
            )
        if "contact" in msg or "agent" in msg:
            return (
                "You can reach our customer support anytime:\n"
                "Email: support@ledxigi.com\nPhone: +91-98765-43210\n"
                "Or continue chatting here for quick help."
            )
        if "complaint" in msg:
            return "Please share your complaint details — we’ll escalate it immediately."
        if "help" in msg or "support" in msg:
            return "I’m here 24/7 to help with LED products, setup, or troubleshooting. How can I assist you?"
        return "Our support team is always available. Could you clarify your concern?"

    # --------------------------------------------------------
    # PRICE HANDLER
    # --------------------------------------------------------
    def _handle_price_query(self, msg: str) -> str:
        if "p2" in msg:
            return "P2.5 indoor panels range from ₹9,000–₹12,000 per sqm."
        if "p3" in msg:
            return "P3.91 panels (indoor/outdoor) range between ₹7,500–₹9,500 per sqm."
        if "p6" in msg or "p10" in msg:
            return "Outdoor P6–P10 panels cost between ₹5,000–₹7,000 per sqm."
        if "controller" in msg:
            return "Controllers range from ₹8,000–₹25,000 depending on model."
        if "power" in msg:
            return "Power supplies start at ₹1,200 (200W) and go up to ₹2,500 (500W)."
        return "Please specify the product (e.g., 'P3.91 price' or 'controller cost')."

    # --------------------------------------------------------
    # ORDER / REPLACEMENT HANDLER
    # --------------------------------------------------------
    def _handle_order_query(self, msg: str) -> str:
        if "track" in msg or "status" in msg or "delivery" in msg:
            return (
                "To track your order, please share your order ID.\n"
                "Example: 'Track order #LEDX1234'."
            )
        if "replacement" in msg or "refund" in msg:
            return (
                "Replacement requests are eligible within 7 days of delivery.\n"
                "Please provide your order ID and product issue to proceed."
            )
        if "order" in msg or "dispatch" in msg:
            return (
                "Orders are usually processed within 24–48 hours.\n"
                "Would you like an update on a specific order?"
            )
        return "Could you clarify if you want to track, replace, or check order details?"

    # --------------------------------------------------------
    # AI KNOWLEDGEBASE FALLBACK
    # --------------------------------------------------------
    def _ai_knowledge_response(self, message: str) -> str:
        try:
            results = self.vector_db.similarity_search(message, k=3)
            context = "\n".join([doc.page_content for doc in results])
            prompt = f"Answer the question based on the context below:\nContext:\n{context}\nQuestion: {message}"
            answer = self.llm(prompt)
            return answer
        except Exception:
            return "I’m sorry, I don’t have information on that yet. Could you rephrase or ask another question?"

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------
    def _is_greeting(self, msg: str) -> bool:
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]
        return any(word in msg for word in greetings)

    def _build_response(self, reply: str) -> dict:
        return {"session_id": self.session_id, "reply": reply}

    def _build_buttons_response(self, reply: str, buttons: list) -> dict:
        return {"session_id": self.session_id, "reply": reply, "type": "buttons", "buttons": buttons}
  
  